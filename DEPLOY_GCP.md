# 🚀 Guia de Hospedagem Gratuita no Google Cloud (Compute Engine - Free Tier)

Este guia ensina o passo a passo para colocar o **Assistente Fran** no ar 24 horas por dia, 7 dias por semana, utilizando a cota **100% gratuita perpétua** do Google Cloud.

---

## 📌 Requisitos da Cota Gratuita (Sempre Gratuito / Free Tier)
Para garantir que o Google **não cobre nada**, configure os campos exatamente como abaixo:

| Campo | Configuração Obrigatória para ser Grátis |
| :--- | :--- |
| **Região** | `us-central1` (Iowa), `us-east1` (South Carolina) ou `us-west1` (Oregon) |
| **Série da Máquina** | `E2` |
| **Tipo de Máquina** | `e2-micro` (2 vCPUs, 1 GB de RAM) |
| **Disco de Inicialização** | Até **30 GB** do tipo **Disco Permanente Padrão (HDD)** |
| **Sistema Operacional** | **Ubuntu 22.04 LTS** (ou Debian 12) |

---

## Passo 1: Criar a Máquina Virtual (VM) no Google Cloud Console

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. No menu lateral esquerdo (☰), vá em **Compute Engine** > **Instâncias de VM**.
3. Clique no botão **Criar Instância** no topo da página.
4. Preencha o formulário com as seguintes opções:
   - **Nome**: `assistente-fran-vm`
   - **Região**: Escolha `us-central1 (Iowa)` ou `us-east1 (Carolina do Sul)`.
   - **Zona**: Qualquer uma (ex: `us-central1-a`).
   - **Configuração da máquina**:
     - Série: `E2`
     - Tipo de máquina: Selecione `e2-micro` *(aparecerá um aviso indicando elegibilidade para a cota gratuita)*.
   - **Disco de inicialização**:
     - Clique em **Alterar**.
     - Sistema operacional: `Ubuntu`.
     - Versão: `Ubuntu 22.04 LTS`.
     - Tipo de disco: `Disco permanente padrão` (Standard persistent disk).
     - Tamanho: `30` GB.
     - Clique em **Selecionar**.
   - **Firewall**:
     - Marque ☑ **Permitir tráfego HTTP**.
     - Marque ☑ **Permitir tráfego HTTPS**.
5. Clique em **Criar** no final da página e aguarde 1 minuto até a VM iniciar (ficará com um ícone verde de check ✔).

---

## Passo 2: Conectar na Máquina via Terminal SSH

1. Na lista de instâncias de VM, ao lado do nome `assistente-fran-vm`, clique no botão **SSH**.
2. Uma janela preta de terminal abrirá diretamente no seu navegador conectando à máquina.

---

## Passo 3: Enviar o Projeto para a Máquina

Você tem duas formas fáceis de transferir o código:

### Opção A: Pelo GitHub (Mais recomendada)
No terminal SSH da VM, execute:
```bash
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git assistente-fran
cd assistente-fran
```

### Opção B: Upload direto pelo Navegador
1. No seu computador, compacte a pasta do projeto em um arquivo `.zip` (não precisa incluir a pasta `venv`).
2. Na janela SSH do navegador, clique no ícone de **engrenagem** ⚙ no canto superior direito e selecione **Upload file**.
3. Escolha o arquivo `.zip` do seu computador e aguarde o envio.
4. No terminal da VM, descompacte com:
```bash
sudo apt update && sudo apt install -y unzip
unzip Assistente_Fran.zip -d assistente-fran
cd assistente-fran
```

---

## Passo 4: Executar o Script de Deploy Automático

Dentro da pasta do projeto na VM, basta rodar:

```bash
chmod +x deploy_gcp.sh
./deploy_gcp.sh
```

O script cuidará de tudo automaticamente:
- Cria 2GB de memória Swap (evita falta de memória na VM).
- Instala Python, Nginx e dependências.
- Configura o serviço de inicialização automática do Flask com Gunicorn.
- Configura o servidor web Nginx como proxy reverso na porta 80.
- Inicia o sistema e exibe o IP de acesso.

---

## Passo 5: Acessar a Aplicação

Ao terminar a execução, o terminal exibirá:
```
🔗 Acesse pelo navegador no endereço:
   http://IP_EXTERNO_DA_SUA_VM
```

Basta colar esse endereço no seu navegador para usar a plataforma!

---

## 🛠 Comandos de Gestão no Servidor

Caso queira gerenciar a aplicação no futuro pelo terminal SSH:

- **Ver status do sistema**:
  ```bash
  sudo systemctl status assistente-fran
  ```
- **Reiniciar o servidor**:
  ```bash
  sudo systemctl restart assistente-fran
  ```
- **Ver logs em tempo real**:
  ```bash
  sudo journalctl -u assistente-fran -f
  ```
- **Reiniciar o Nginx**:
  ```bash
  sudo systemctl restart nginx
  ```
