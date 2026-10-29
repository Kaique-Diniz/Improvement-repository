// Executado apenas pelo diagnóstico Windows. Nenhuma API de escrita de ACL.
using System;
using System.IO;
using System.Globalization;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Security.Cryptography;
using Microsoft.Win32.SafeHandles;

public static class ConversorAclProbe {
    const uint ReadControlAttributes = 0x20080, ShareReadWrite = 3;
    const uint BackupAndOpenReparsePoint = 0x02200000;
    [StructLayout(LayoutKind.Sequential)] struct FileInfoNative {
        public uint Attributes, CreationLow, CreationHigh, AccessLow, AccessHigh;
        public uint WriteLow, WriteHigh, Volume, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern SafeFileHandle CreateFileW(string path,uint access,uint share,IntPtr attrs,uint disposition,uint flags,IntPtr template);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool GetFileInformationByHandle(SafeFileHandle handle,out FileInfoNative info);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle,StringBuilder path,uint length,uint flags);
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr ptr);
    [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool OpenProcessToken(IntPtr process,uint access,out IntPtr token);
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode)]
    static extern uint GetNamedSecurityInfoW(string path,uint kind,uint info,out IntPtr owner,out IntPtr group,out IntPtr dacl,out IntPtr sacl,out IntPtr sd);
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, EntryPoint="GetNamedSecurityInfoW", ExactSpelling=true)]
    static extern uint GetNamedSelected5(string path,uint kind,uint info,out IntPtr owner,IntPtr group,out IntPtr dacl,IntPtr sacl,out IntPtr sd);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)]
    static extern int GetCurrentPackageFullName(ref uint length,IntPtr buffer);
    [DllImport("advapi32.dll",SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr token,uint kind,out uint value,uint capacity,out uint length);
    [DllImport("advapi32.dll")]
    static extern uint GetSecurityInfo(SafeFileHandle handle,uint kind,uint info,out IntPtr owner,out IntPtr group,out IntPtr dacl,out IntPtr sacl,out IntPtr sd);
    [DllImport("advapi32.dll")] static extern uint GetSecurityDescriptorLength(IntPtr sd);
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern bool GetFileSecurityW(string path,uint info,byte[] sd,uint length,out uint needed);
    [DllImport("advapi32.dll",SetLastError=true)]
    static extern bool GetSecurityDescriptorDacl(IntPtr sd,out int present,out IntPtr dacl,out int defaulted);
    [DllImport("advapi32.dll",SetLastError=true)]
    static extern bool GetAce(IntPtr acl,uint index,out IntPtr ace);

    static string Digest(byte[] key,string domain,byte[] bytes) {
        byte[] prefix=Encoding.UTF8.GetBytes(domain+"\0"), data=new byte[prefix.Length+bytes.Length];
        Buffer.BlockCopy(prefix,0,data,0,prefix.Length);Buffer.BlockCopy(bytes,0,data,prefix.Length,bytes.Length);
        using(HMACSHA256 h=new HMACSHA256(key)) return BitConverter.ToString(h.ComputeHash(data)).Replace("-","").ToLowerInvariant();
    }
    static string Id(byte[] key,string domain,string value) {return Digest(key,domain,Encoding.UTF8.GetBytes(value));}
    static Dictionary<string,object> D() {return new Dictionary<string,object>();}
    static byte[] CopyDescriptor(IntPtr sd) {
        if(sd==IntPtr.Zero) throw new InvalidOperationException();
        uint size=GetSecurityDescriptorLength(sd);
        if(size<20 || size>1048576) throw new InvalidOperationException();
        byte[] raw=new byte[(int)size];Marshal.Copy(sd,raw,0,(int)size);return raw;
    }
    static byte[] Named(string path,uint info) {
        IntPtr owner,group,dacl,sacl,sd=IntPtr.Zero;
        try {uint code=GetNamedSecurityInfoW(path,1,info,out owner,out group,out dacl,out sacl,out sd);
            if(code!=0) throw new InvalidOperationException();return CopyDescriptor(sd);
        } finally {if(sd!=IntPtr.Zero) LocalFree(sd);}
    }
    static byte[] NamedSelected(string path) {
        IntPtr owner,dacl,sd=IntPtr.Zero;
        try {uint code=GetNamedSelected5(path,1,5,out owner,IntPtr.Zero,out dacl,IntPtr.Zero,out sd);
            if(code!=0)throw new InvalidOperationException();return CopyDescriptor(sd);
        }finally{if(sd!=IntPtr.Zero)LocalFree(sd);}
    }
    static byte[] Handle(SafeFileHandle handle,uint info) {
        IntPtr owner,group,dacl,sacl,sd=IntPtr.Zero;
        try {uint code=GetSecurityInfo(handle,1,info,out owner,out group,out dacl,out sacl,out sd);
            if(code!=0) throw new InvalidOperationException();return CopyDescriptor(sd);
        } finally {if(sd!=IntPtr.Zero) LocalFree(sd);}
    }
    static byte[] FileSecurity(string path,uint info) {
        uint size;GetFileSecurityW(path,info,null,0,out size);
        if(size<20 || size>1048576) throw new InvalidOperationException();
        byte[] raw=new byte[(int)size];uint needed;
        if(!GetFileSecurityW(path,info,raw,size,out needed) || needed!=size) throw new InvalidOperationException();
        return raw;
    }
    static string Classify(string sid,string user) {
        if(sid==user) return "usuario";
        switch(sid) {
            case "S-1-5-18":return "system";
            case "S-1-5-32-544":return "administradores";
            case "S-1-3-0":return "creator_owner";
            case "S-1-3-1":return "creator_group";
            case "S-1-3-4":return "owner_rights";
            case "S-1-1-0":return "everyone";
            case "S-1-5-11":return "authenticated_users";
            default:return "outra";
        }
    }
    static Dictionary<string,object> Rule(byte[] key,string user,int type,int flags,uint mask,string sid) {
        Dictionary<string,object> r=D();r["tipo"]=type;r["flags"]=flags;r["mascara"]=String.Format("0x{0:x}",mask);
        r["identidade"]=Id(key,"sid",sid);r["classe"]=Classify(sid,user);return r;
    }
    static List<object> GetAceRules(byte[] raw,byte[] key,string user,RawAcl acl) {
        List<object> rules=new List<object>();GCHandle pin=GCHandle.Alloc(raw,GCHandleType.Pinned);
        try {
            int present,def;IntPtr dacl;
            if(!GetSecurityDescriptorDacl(pin.AddrOfPinnedObject(),out present,out dacl,out def))throw new InvalidOperationException();
            if(acl==null) {if(dacl!=IntPtr.Zero)throw new InvalidOperationException();return rules;}
            long start=pin.AddrOfPinnedObject().ToInt64(), end=start+raw.Length, d=dacl.ToInt64();
            if(d<start || d+8>end)throw new InvalidOperationException();
            int aclSize=(ushort)Marshal.ReadInt16(dacl,2);long aclEnd=d+aclSize;
            if(aclSize<8 || aclEnd>end || (ushort)Marshal.ReadInt16(dacl,4)!=acl.Count)throw new InvalidOperationException();
            for(uint i=0;i<acl.Count;i++) {
                IntPtr ace;if(!GetAce(dacl,i,out ace))throw new InvalidOperationException();
                long a=ace.ToInt64();if(a<d+8 || a+4>aclEnd)throw new InvalidOperationException();
                int type=Marshal.ReadByte(ace),flags=Marshal.ReadByte(ace,1),size=(ushort)Marshal.ReadInt16(ace,2);
                if(size<4 || size%4!=0 || a+size>aclEnd)throw new InvalidOperationException();
                if(type==0 || type==1) {
                    if(size<16)throw new InvalidOperationException();
                    int n=Marshal.ReadByte(ace,9);if(n>15 || 16+4*n!=size)throw new InvalidOperationException();
                    byte[] sid=new byte[size-8];Marshal.Copy(IntPtr.Add(ace,8),sid,0,sid.Length);
                    string value=new SecurityIdentifier(sid,0).Value;
                    rules.Add(Rule(key,user,type,flags,unchecked((uint)Marshal.ReadInt32(ace,4)),value));
                } else {rules.Add(Rule(key,user,type,flags,0,""));}
            }
            return rules;
        } finally {pin.Free();}
    }
    static Dictionary<string,object> Project(byte[] raw,byte[] key,string user) {
        if(raw.Length<20 || raw.Length>1048576)throw new InvalidOperationException();
        RawSecurityDescriptor sd=new RawSecurityDescriptor(raw,0);Dictionary<string,object> result=D();
        result["estado"]="ok";result["bytes"]=raw.Length;result["binario_hmac"]=Digest(key,"sd",raw);
        result["control_flags"]=(int)sd.ControlFlags;
        result["usuario"]=Id(key,"sid",user);result["proprietario"]=Id(key,"sid",sd.Owner==null?"":sd.Owner.Value);
        result["grupo"]=Id(key,"sid",sd.Group==null?"":sd.Group.Value);
        result["dacl_presente"]=(sd.ControlFlags&ControlFlags.DiscretionaryAclPresent)!=0 && sd.DiscretionaryAcl!=null;
        List<object> rules=new List<object>();
        if(sd.DiscretionaryAcl!=null) foreach(GenericAce ace in sd.DiscretionaryAcl) {
            KnownAce known=ace as KnownAce;int type=(int)ace.AceType;
            rules.Add(Rule(key,user,type,(int)ace.AceFlags,known==null?0:unchecked((uint)known.AccessMask),known==null?"":known.SecurityIdentifier.Value));
        }
        result["regras"]=rules;result["GetAce"]=GetAceRules(raw,key,user,sd.DiscretionaryAcl);
        uint offset=BitConverter.ToUInt32(raw,16);
        if((bool)result["dacl_presente"]) {
            if(offset>raw.Length-8)throw new InvalidOperationException();
            int count=BitConverter.ToUInt16(raw,(int)offset+2);
            if(count<8 || (long)offset+count>raw.Length)throw new InvalidOperationException();
            byte[] dacl=new byte[count];Buffer.BlockCopy(raw,(int)offset,dacl,0,count);
            result["dacl_hmac"]=Digest(key,"dacl",dacl);
        } else result["dacl_hmac"]=Digest(key,"dacl",new byte[0]);
        return result;
    }
    static void Capture(Dictionary<string,object> sources,string name,Func<byte[]> read,byte[] key,string user,uint? info,string origin) {
        Dictionary<string,object> r;
        try {r=Project(read(),key,user);}catch {r=D();r["estado"]="nao_comprovado";}
        r["security_information"]=info;r["origem"]=origin;
        Dictionary<string,object> outputs=null;
        if(name.Contains("Named") || name.StartsWith("Roundtrip_",StringComparison.Ordinal)) {
            bool selected=name=="Named_5_selected" || name=="Python_Named_5";
            outputs=D();outputs["owner"]=true;outputs["group"]=!selected;outputs["dacl"]=true;outputs["sacl"]=!selected;
        }
        r["saidas_opcionais"]=outputs;sources[name]=r;
    }
    static string NormalPath(string path) {
        if(path.StartsWith(@"\\?\UNC\",StringComparison.OrdinalIgnoreCase))return @"\\"+path.Substring(8);
        if(path.StartsWith(@"\\?\",StringComparison.OrdinalIgnoreCase))return path.Substring(4);
        return path;
    }
    static FileInfoNative Info(SafeFileHandle handle) {
        FileInfoNative info;
        if(!GetFileInformationByHandle(handle,out info) || (info.Attributes&0x400)!=0)throw new InvalidOperationException();
        return info;
    }
    static string FormatId(FileInfoNative info) {
        return String.Format(CultureInfo.InvariantCulture,"{0:x8}:{1:x8}:{2:x8}",info.Volume,info.IndexHigh,info.IndexLow);
    }
    static string ObjectId(SafeFileHandle handle,byte[] key,out bool directory) {
        FileInfoNative info=Info(handle);directory=(info.Attributes&0x10)!=0;
        return Id(key,"objeto",FormatId(info));
    }
    static bool EqualPath(string a,string b) {
        return String.Equals(NormalPath(a).TrimEnd('\\','/'),NormalPath(b).TrimEnd('\\','/'),StringComparison.OrdinalIgnoreCase);
    }
    static void IdentityDetails(Dictionary<string,object> checks,SafeFileHandle handle,byte[] key,string user,string full,string final,Dictionary<string,string> meta) {
        FileInfoNative info=Info(handle);string formatted=FormatId(info);
        checks["hmac_vetor_igual"]=meta["hmac_vetor"]==Digest(key,"instrumentacao",new byte[]{0,1,127,128,255});
        checks["layout_tamanho_igual"]=meta["layout_tamanho"]==Marshal.SizeOf(typeof(FileInfoNative)).ToString(CultureInfo.InvariantCulture);
        string[] fields={"Attributes","CreationLow","CreationHigh","AccessLow","AccessHigh","WriteLow","WriteHigh","Volume","SizeHigh","SizeLow","Links","IndexHigh","IndexLow"};
        List<string> offsets=new List<string>();
        foreach(string field in fields)offsets.Add(Marshal.OffsetOf(typeof(FileInfoNative),field).ToInt32().ToString(CultureInfo.InvariantCulture));
        checks["layout_offsets_iguais"]=meta["layout_offsets"]==Id(key,"layout_offsets",String.Join(",",offsets.ToArray()));
        checks["volume_igual"]=meta["volume"]==Id(key,"objeto_volume",info.Volume.ToString("x8",CultureInfo.InvariantCulture));
        checks["indice_alto_igual"]=meta["indice_alto"]==Id(key,"objeto_indice_alto",info.IndexHigh.ToString("x8",CultureInfo.InvariantCulture));
        checks["indice_baixo_igual"]=meta["indice_baixo"]==Id(key,"objeto_indice_baixo",info.IndexLow.ToString("x8",CultureInfo.InvariantCulture));
        checks["serializacao_igual"]=meta["serializacao"]==Id(key,"objeto_formatacao",formatted);
        checks["identidade_total_igual"]=meta["identidade"]==Id(key,"objeto",formatted);
        checks["arquitetura_igual"]=meta["ponteiro_bits"]==(IntPtr.Size*8).ToString(CultureInfo.InvariantCulture);
        checks["usuario_processo_igual"]=meta["usuario"]==Id(key,"sid",user);
        checks["caminho_final_python_igual_csharp"]=EqualPath(meta["caminho_final"],final);
        checks["caminho_python_igual_solicitado"]=EqualPath(meta["caminho_final"],full);
        checks["caminho_csharp_igual_solicitado_normalizado"]=EqualPath(final,full);
        uint needed=0;int code;
        try {code=GetCurrentPackageFullName(ref needed,IntPtr.Zero);}catch{code=-1;}
        bool known=code==122 || code==15700,present=code==122 && needed>0;
        checks["pacote_python_verificavel"]=meta["pacote_verificavel"]=="1";
        checks["pacote_csharp_verificavel"]=known;
        checks["pacote_python_presente"]=meta["pacote_presente"]=="1";
        checks["pacote_csharp_presente"]=present;
        checks["pacote_presenca_igual"]=known && meta["pacote_verificavel"]=="1" && (meta["pacote_presente"]=="1")==present;
    }
    static void TokenDetails(Dictionary<string,object> checks,IntPtr token,Dictionary<string,string> meta) {
        string[] names={"appcontainer","elevacao","virtualizacao"};uint[] types={29,20,24};
        for(int i=0;i<names.Length;i++) {
            uint value,length;bool known=GetTokenInformation(token,types[i],out value,4,out length) && length==4 && value<=1;
            string prefix="token_"+names[i];string mk=prefix+"_verificavel";
            bool both=known && meta.ContainsKey(mk) && meta[mk]=="1";
            checks[prefix+"_verificavel"]=both;
            checks[prefix+"_igual"]=both && (meta[prefix]=="1")== (value==1);
        }
    }
    static SafeFileHandle Open(string path) {
        SafeFileHandle h=CreateFileW(path,ReadControlAttributes,ShareReadWrite,IntPtr.Zero,3,BackupAndOpenReparsePoint,IntPtr.Zero);
        if(h.IsInvalid){h.Dispose();throw new InvalidOperationException();}return h;
    }
    static FileSystemSecurity DotNet(string path,bool directory,AccessControlSections sections) {
        return directory?(FileSystemSecurity)new DirectorySecurity(path,sections):new System.Security.AccessControl.FileSecurity(path,sections);
    }
    public static Dictionary<string,object> Run(string path,byte[] key,byte[] pythonNamed,byte[] pythonFile,byte[] pythonAll,Dictionary<string,string> meta,Func<FileSystemSecurity> readGetAcl) {
        Dictionary<string,object> result=D(),sources=D(),checks=D();IntPtr token;
        if(!OpenProcessToken(GetCurrentProcess(),8,out token))throw new InvalidOperationException();
        string user;
        try {using(WindowsIdentity w=new WindowsIdentity(token))user=w.User.Value;TokenDetails(checks,token,meta);}finally{CloseHandle(token);}
        using(WindowsIdentity effective=WindowsIdentity.GetCurrent())
            result["identidade_efetiva_igual_processo"]=effective.User.Value==user;
        result["ponteiro_bits"]=IntPtr.Size*8;
        string full=Path.GetFullPath(path);result["caminho_solicitado_hmac"]=Id(key,"path",full.ToUpperInvariant());
        if((File.GetAttributes(full)&FileAttributes.ReparsePoint)!=0)throw new InvalidOperationException();
        string parent=Path.GetDirectoryName(full);
        for(DirectoryInfo ancestor=parent==null?null:new DirectoryInfo(parent);ancestor!=null;ancestor=ancestor.Parent)
            if((ancestor.Attributes&FileAttributes.ReparsePoint)!=0)throw new InvalidOperationException();
        using(SafeFileHandle handle=Open(full)) {
            bool directory;string objectId=ObjectId(handle,key,out directory);
            StringBuilder finalPath=new StringBuilder(32768);uint finalSize=GetFinalPathNameByHandleW(handle,finalPath,(uint)finalPath.Capacity,0);
            if(finalSize==0 || finalSize>=finalPath.Capacity)throw new InvalidOperationException();
            result["objeto_antes_hmac"]=objectId;result["diretorio"]=directory;
            result["caminho_final_igual_solicitado"]=String.Equals(full,NormalPath(finalPath.ToString()),StringComparison.OrdinalIgnoreCase);
            result["caminho_final_hmac"]=Id(key,"path",NormalPath(finalPath.ToString()).ToUpperInvariant());
            result["handle_sem_share_delete"]=true;result["objeto_tipo"]=1;
            IdentityDetails(checks,handle,key,user,full,finalPath.ToString(),meta);
            Capture(sources,"Named_5_selected",delegate{return NamedSelected(full);},key,user,5,"GetNamedSecurityInfoW_NULL_group_sacl");
            foreach(uint info in new uint[]{5,7}) {
                uint flags=info;string suffix=info.ToString();
                Capture(sources,"Named_"+suffix,delegate{return Named(full,flags);},key,user,flags,"GetNamedSecurityInfoW");
                Capture(sources,"File_"+suffix,delegate{return FileSecurity(full,flags);},key,user,flags,"GetFileSecurityW");
                Capture(sources,"Handle_"+suffix,delegate{return Handle(handle,flags);},key,user,flags,"GetSecurityInfo");
                AccessControlSections sections=AccessControlSections.Owner|AccessControlSections.Access;
                if(info==7)sections|=AccessControlSections.Group;
                AccessControlSections selected=sections;
                Capture(sources,"DotNet_"+suffix,delegate{return DotNet(full,directory,selected).GetSecurityDescriptorBinaryForm();},key,user,flags,"FileSystemSecurity");
            }
            FileSystemSecurity psAcl=readGetAcl();
            byte[] psBefore=psAcl.GetSecurityDescriptorBinaryForm();
            Capture(sources,"GetAcl",delegate{return psBefore;},key,user,null,"Get-Acl");
            List<object> accessRules=new List<object>();
            foreach(FileSystemAccessRule rule in psAcl.GetAccessRules(true,true,typeof(SecurityIdentifier))) {
                int flags=0;
                if((rule.InheritanceFlags&InheritanceFlags.ContainerInherit)!=0)flags|=2;
                if((rule.InheritanceFlags&InheritanceFlags.ObjectInherit)!=0)flags|=1;
                if((rule.PropagationFlags&PropagationFlags.NoPropagateInherit)!=0)flags|=4;
                if((rule.PropagationFlags&PropagationFlags.InheritOnly)!=0)flags|=8;
                if(rule.IsInherited)flags|=16;
                accessRules.Add(Rule(key,user,(int)rule.AccessControlType,flags,unchecked((uint)rule.FileSystemRights),rule.IdentityReference.Value));
            }
            result["GetAccessRules"]=accessRules;
            Capture(sources,"GetAcl_depois",delegate{return psAcl.GetSecurityDescriptorBinaryForm();},key,user,null,"Get-Acl_apos_GetAccessRules");
            Capture(sources,"Python_Named_5",delegate{return pythonNamed;},key,user,5,"ctypes_GetNamedSecurityInfoW");
            Capture(sources,"Python_File_5",delegate{return pythonFile;},key,user,5,"ctypes_GetFileSecurityW");
            Capture(sources,"Python_Named_5_all",delegate{return pythonAll;},key,user,5,"ctypes_GetNamedSecurityInfoW_all_outputs");
            checks["reabertura_final_python_disponivel"]=false;checks["reabertura_final_python_mesmo_objeto"]=false;
            Func<byte[]> missing=delegate{throw new InvalidOperationException();};
            Capture(sources,"Python_final_Named_5",missing,key,user,5,"GetNamedSecurityInfoW_python_final");
            Capture(sources,"Python_final_File_5",missing,key,user,5,"GetFileSecurityW_python_final");
            Capture(sources,"Python_final_Handle_5",missing,key,user,5,"GetSecurityInfo_python_final");
            try {
                using(SafeFileHandle pyFinal=Open(meta["caminho_final"])) {
                    bool ignored;string pyId=ObjectId(pyFinal,key,out ignored);
                    checks["reabertura_final_python_disponivel"]=true;
                    checks["reabertura_final_python_mesmo_objeto"]=pyId==meta["identidade"];
                    if(pyId==meta["identidade"]) {
                        Capture(sources,"Python_final_Named_5",delegate{return Named(meta["caminho_final"],5);},key,user,5,"GetNamedSecurityInfoW_python_final");
                        Capture(sources,"Python_final_File_5",delegate{return FileSecurity(meta["caminho_final"],5);},key,user,5,"GetFileSecurityW_python_final");
                        Capture(sources,"Python_final_Handle_5",delegate{return Handle(pyFinal,5);},key,user,5,"GetSecurityInfo_python_final");
                    }
                }
            }catch {}
            Capture(sources,"Roundtrip_Raw_5",delegate{
                RawSecurityDescriptor sd=new RawSecurityDescriptor(Named(full,5),0);byte[] raw=new byte[sd.BinaryLength];sd.GetBinaryForm(raw,0);return raw;
            },key,user,5,"RawSecurityDescriptor_memoria");
            Capture(sources,"Roundtrip_Common_5",delegate{
                CommonSecurityDescriptor sd=new CommonSecurityDescriptor(directory,false,Named(full,5),0);byte[] raw=new byte[sd.BinaryLength];sd.GetBinaryForm(raw,0);return raw;
            },key,user,5,"CommonSecurityDescriptor_memoria");
            // Segunda leitura detecta alteração durante o diagnóstico, sem tentar corrigi-la.
            Capture(sources,"Handle_5_depois",delegate{return Handle(handle,5);},key,user,5,"GetSecurityInfo");
            using(SafeFileHandle after=Open(full)) {
                bool ignored;result["objeto_depois_hmac"]=ObjectId(after,key,out ignored);
            }
            bool ignored2;result["handle_estavel"]=objectId==ObjectId(handle,key,out ignored2);
        }
        result["comparacao_identidade"]=checks;result["fontes"]=sources;return result;
    }
}
