"""Metadados administrativos de sessão; não persiste relatórios nem identidades pessoais."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from conversor.domain.canonical import Endereco, Unidade
from conversor.export.identifiers import EnderecoPadrao, OrigemEnderecoUsuario, selecionar_perfil
from conversor.readers.text_support import ErroLeitura
from .service import PERFIS, PERFIS_SAIDA_PATH, reconhecer, ler


class EnderecoLocal(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    logradouro: str = Field(min_length=1, max_length=200)
    numero: str = Field(default='', max_length=30)
    cep: str = Field(default='', pattern=r'^(?:[0-9]{8})?$')
    bairro: str = Field(default='', max_length=120)
    cidade: str = Field(default='', max_length=120)
    uf: str = Field(default='', pattern=r'^(?:[A-Z]{2})?$')


class MapeamentoLocal(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    bloco: str = Field(max_length=20, pattern=r'^[A-Za-z0-9 ._-]*$')
    codigo: str = Field(min_length=1, max_length=12, pattern=r'^[A-Z0-9]+$')


class ConfiguracaoLocal(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    revisao_esperada: int = Field(ge=0)
    endereco: EnderecoLocal | None = None
    mapeamentos: list[MapeamentoLocal] = Field(default_factory=list, max_length=50)


class ContextosLocais:
    def __init__(self, runtime):
        self.runtime = runtime
        self.contextos, self.configs = {}, {}

    def limpar(self, now):
        self.contextos = {k:v for k,v in self.contextos.items()
            if v['owner'] in self.runtime.sessions and v['prazo'] > now}
        self.configs = {k:v for k,v in self.configs.items() if k[0] in self.runtime.sessions}

    def criar(self, raw, owner, escolha='auto'):
        perfil, codigo, leitor = reconhecer(raw, perfil_informado=escolha)
        if escolha != 'auto' and perfil['id'] != escolha:
            raise ErroLeitura('IDENTIDADE_DOCUMENTAL_CONFLITANTE')
        lote, _ = ler(raw, perfil, codigo, leitor, 'inadimplencia')
        if len(lote.unidades)>5000:
            raise HTTPException(413,'LIMITE_DE_UNIDADES')
        with self.runtime.lock:
            self.runtime.limpar()
            if len(self.contextos)>=32:
                raise HTTPException(429,'LIMITE_DE_CONTEXTOS')
            unidades=[u.model_dump(mode='json') for u in lote.unidades]
            tamanho=len(json.dumps(unidades,ensure_ascii=False).encode('utf-8'))
            if tamanho+sum(c['tamanho'] for c in self.contextos.values())>8*1024*1024:
                raise HTTPException(503,'LIMITE_DE_METADADOS_DE_SESSAO')
            id_=secrets.token_urlsafe(24)
            self.contextos[id_]={'owner':owner,'prazo':self.runtime.relogio()+900,
                'perfil':perfil['id'],'sha256':sha256(raw).hexdigest(),
                'unidades':unidades,'tamanho':tamanho}
            return self.consultar(id_,owner)

    def obter(self,id_,owner):
        self.runtime.limpar()
        ctx=self.contextos.get(id_)
        if not ctx or ctx['owner']!=owner:
            raise HTTPException(404,'CONTEXTO_INDISPONIVEL')
        return ctx

    def consultar(self,id_,owner):
        with self.runtime.lock:
            ctx=self.obter(id_,owner);p=PERFIS[ctx['perfil']]
            config=self.configs.get((owner,p['id']),{})
            saida=selecionar_perfil(json.loads(PERFIS_SAIDA_PATH.read_bytes()),
                administradora_id=p['administradora_id'],condominio_id=p['condominio_id'])
            unidades=[]
            for raw in ctx['unidades']:
                u=Unidade.model_validate(raw)
                try:
                    if saida is None:raise ErroLeitura('PERFIL_SAIDA_NAO_CONFIGURADO')
                    cedente,comp=saida.codificar(u,administradora_id=p['administradora_id'])
                    estado='comprovado'
                except ErroLeitura:
                    cedente=comp='';estado='pendente'
                unidades.append({'bloco':u.bloco_original,'unidade':u.unidade_original,
                    'cedente':cedente,'complemento':comp,'estado':estado})
            mapeamentos=[]
            for item in config.get('mapeamentos',[]):
                documentado=saida.torres.get(item['bloco']) if saida else None
                estado=('comprovado' if documentado==item['codigo'] else
                    'conflitante' if documentado is not None else 'pendente')
                mapeamentos.append(dict(item,estado=estado,aplicado=estado=='comprovado'))
            padrao=config.get('padrao')
            return {'contexto':id_,'perfil':p['id'],'nome':p['nome'],'administradora':p['administradora'],
                'administradora_id':p['administradora_id'],'condominio_id':p['condominio_id'],
                'revisao':config.get('revisao',0),'endereco':padrao.endereco.model_dump(mode='json',exclude={'complemento'}) if padrao else None,
                'mapeamentos':mapeamentos,'unidades':unidades,
                'limite':'Formato documentado não comprova pertencimento ou titularidade. Propostas sem prova não alteram codificação ou seleção. Metadados somente desta sessão.'}

    def salvar(self,id_,owner,dados):
        with self.runtime.lock:
            ctx=self.obter(id_,owner);p=PERFIS[ctx['perfil']];key=(owner,p['id'])
            current=self.configs.get(key,{})
            if dados.revisao_esperada!=current.get('revisao',0):
                raise HTTPException(409,'CONFIGURACAO_ALTERADA_RECARREGUE')
            if len({m.bloco for m in dados.mapeamentos})!=len(dados.mapeamentos):
                raise HTTPException(422,'MAPEAMENTO_AMBIGUO')
            revision=current.get('revisao',0)+1
            padrao=EnderecoPadrao(endereco=Endereco(**dados.endereco.model_dump()),evidencia=OrigemEnderecoUsuario(
                registro_id='endereco_'+p['id'],versao=revision,registrado_em=datetime.now(timezone.utc),
                sessao_sha256=sha256(owner.encode()).hexdigest())) if dados.endereco else None
            self.configs[key]={'revisao':revision,'padrao':padrao,
                'mapeamentos':[m.model_dump() for m in dados.mapeamentos]}
            return self.consultar(id_,owner)

    def buscar_endereco(self,owner,administradora_id,condominio_id):
        with self.runtime.lock:
            if not self.runtime.autenticar(owner):return None
            perfil=next((p for p in PERFIS.values() if (p['administradora_id'],p['condominio_id'])==
                (administradora_id,condominio_id)),None)
            return self.configs.get((owner,perfil['id']),{}).get('padrao') if perfil else None
