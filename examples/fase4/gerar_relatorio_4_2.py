"""Demonstração fixa e 100% sintética; não aceita documentos ou planos externos."""
import argparse
from collections import Counter
from datetime import datetime,timezone,timedelta,date
from hashlib import sha256
import json
from pathlib import Path
import secrets
import tempfile
from types import SimpleNamespace

from conversor.adapters.billing_authority import AutoridadeHMAC
from conversor.adapters.billing_evaluation_authority import VerificadorPlanosJSON
from conversor.adapters.billing_json import RepositorioPlanosJSON
from conversor.application.billing_ports import CredencialOperador
from conversor.application.billing_evaluation import SimularCobranca
from conversor.application.ports import ErroAplicacao
from conversor.domain.billing_rules import PlanoCobranca,ComandoPlano,hash_modelo
from conversor.domain.billing_evaluation import EntradaSimulacao,SolicitacaoSimulacao,FatoEvidenciado
from conversor.domain.canonical import LoteCanonico,Unidade,Boleto,Origem,Ocorrencia


def demonstrar():
    cid='cond_demo_sintetico'
    def origem(id_):
        return Origem(arquivo_id=id_,sha256=sha256(('CONTEUDO SINTETICO '+id_).encode()).hexdigest(),
            leitor_versao='fixture_demonstracao4.2',pagina=1,linha=1,identificador='linha_1')
    fonte=origem('requisito_didatico')
    def pred(fato_id):return {'tipo':'fato','fato_id':fato_id,'operador':'eq','valor':{'tipo':'booleano','valor':True}}
    plano=PlanoCobranca(id='plano_demo',condominio_id=cid,versao='1.0.0',natureza='sintetico',
        vigente_de='2026-01-01',vigente_ate='2027-01-01',fontes=(fonte,),
        fatos=({'id':'restricao_didatica','tipo':'booleano','escopo':'unidade'},
               {'id':'permissao_didatica','tipo':'booleano','escopo':'boleto'}),regras=(
            {'id':'exclusao_unidade','prioridade':1,'alvo':'unidade','quando':pred('restricao_didatica'),
             'acao':'excluir','motivo_codigo':'RESTRICAO_SINTETICA','fonte_id':fonte.identificador},
            {'id':'permissao_boleto','prioridade':99,'alvo':'boleto','quando':pred('permissao_didatica'),
             'acao':'incluir','motivo_codigo':'PERMISSAO_SINTETICA','fonte_id':fonte.identificador}))
    unidades=[];boletos=[];fatos=[]
    for n in range(1,5):
        o=origem('canonico_sintetico_'+str(n));uid='unidade_demo_'+str(n);bid='boleto_demo_'+str(n)
        unidades.append(Unidade(id=uid,condominio_id=cid,administradora_id='adm_demo_sintetica',
            bloco_original='BLOCO FICTICIO',unidade_original=str(n),chave_normalizada='demo/'+str(n),
            normalizador_versao='demo1',origem=o))
        boletos.append(Boleto(id=bid,condominio_id=cid,unidade_id=uid,identificador='lancamento_demo_'+str(n),
            vencimento='2026-02-01',competencia=None,composicao={'total_original':'100.00',
                'itens':[{'codigo':'item_demo','valor':'100.00','origem':o}]},origens=(o,)))
        for fid,valor in [('restricao_didatica',n==2),('permissao_didatica',True)]:
            if n==3 and fid=='permissao_didatica':continue
            fatos.append(FatoEvidenciado(id=fid+'_'+str(n),fato_id=fid,condominio_id=cid,unidade_id=uid,
                boleto_id=bid if fid=='permissao_didatica'else None,valor={'tipo':'booleano','valor':valor},
                vigente_de='2026-01-01',vigente_ate='2027-01-01',confirmacao='comprovado',origens=(origem('evidencia_'+fid+'_'+str(n)),)))
    entrada=EntradaSimulacao(lote=LoteCanonico(unidades=tuple(unidades),boletos=tuple(boletos)),
        fatos=tuple(fatos),coberturas_apontamentos=(),ocorrencias_anteriores=(Ocorrencia(id='critico_sintetico',
            processamento_id='leitura_sintetica',codigo='PENDENCIA_SINTETICA',gravidade='critico',escopo='registro',
            registro_id='unidade_demo_4',origem=unidades[3].origem),))
    class Condominios:
        def get_condominio(self,id_):
            if id_!=cid:raise ErroAplicacao('CONDOMINIO_INEXISTENTE')
            return SimpleNamespace(id=cid)
    with tempfile.TemporaryDirectory(prefix='demo-sintetica-4.2-')as local:
        root=Path(local);controle=root/'autoridade';controle.mkdir(mode=0o700)
        key=controle/'chave.bin';key.write_bytes(secrets.token_bytes(32));key.chmod(0o600)
        credencial=CredencialOperador(secrets.token_hex(32))
        registro={'schema_version':'1.0','concessoes':[{'responsavel_id':'operador_demo_sintetico',
            'credencial_sha256':sha256(credencial.segredo.encode()).hexdigest(),
            'acoes':['criar','submeter','aprovar','ativar'],'condominio_ids':[cid],'ambientes':['sintetico']}]}
        path=controle/'operadores.json';path.write_text(json.dumps(registro),encoding='utf-8');path.chmod(0o600)
        repo=RepositorioPlanosJSON(root/'planos',repositorio_id='demo4.2',ambiente='sintetico',
            autoridade=AutoridadeHMAC(controle),condominios=Condominios())
        for n,acao in enumerate(('criar','submeter','aprovar','ativar')):
            comando=ComandoPlano(acao=acao,plano=plano if acao=='criar'else None,plano_id=plano.id,
                em=datetime(2026,2,20,tzinfo=timezone.utc)+timedelta(seconds=n),
                fundamento='EXCLUSIVAMENTE TESTE SINTETICO DESCARTAVEL; NAO OPERACIONAL',evidencia_id='demo_sintetica',
                data_ref=date(2026,2,20)if acao=='ativar'else None)
            repo.executar(comando,credencial=credencial,revisao_esperada=n)
        solicitacao=SolicitacaoSimulacao(processamento_id='demo_4_2_sintetico',condominio_id=cid,
            plano_id=plano.id,plano_versao=plano.versao,plano_hash=hash_modelo(plano),ambiente='sintetico',data_ref='2026-02-20')
        servico=SimularCobranca(repo,VerificadorPlanosJSON(repo))
        relatorio=servico.executar(solicitacao,entrada)
        assert servico.executar(solicitacao,entrada).model_dump_json()==relatorio.model_dump_json()
        return relatorio


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida',required=True,type=Path)
    args=parser.parse_args()
    rel=demonstrar()
    args.saida.write_text(json.dumps(rel.model_dump(mode='json'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'modo':'somente_simulacao_sintetica','decisoes':dict(Counter(d.situacao for d in rel.boletos)),
        'autoriza_cobranca':False,'permite_exportacao_operacional':False}))


if __name__=='__main__':main()
