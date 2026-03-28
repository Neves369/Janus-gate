# 🏛️ Janus' Gate

<p align="center">
  <img width="1408" height="768" alt="janus" src="https://github.com/user-attachments/assets/c64937c5-4db3-4774-8342-6c0565fc839d" />
</p>


### *The threshold between classical infrastructure and digital persistence.*

**Janus' Gate** é uma ferramenta de estudo em segurança ofensiva focada em **Reverse Shell** e persistência. Inspirado no deus romano Jano — o senhor dos portões, dos começos e das transições — o projeto atua como o ponto de entrada (e retorno) entre o sistema alvo e o controlador.

---

## 🛠️ Stack Técnica

| Componente | Tecnologia | Função |
| :--- | :--- | :--- |
| **Engine** | Python 3.x | Core da lógica de rede |
| **Communication** | `socket` | Abstração de baixo nível para TCP/IP |
| **Interface** | CLI / Bash | Interação direta com o shell remoto |

---

obs: O trojan foi escrito para rodar em  sistemas Windows, porém a ferramenta de centro de controle
funciona em ambientes Windows e Linux (testado em UBUNTU e Arch Linux)


## 💻 Como Utilizar

### 1. Executar o Centro de Controle (Atacante)
Na sua máquina execute o arquivo connection.py:

```bash
python3 connection.py
```

### 1. executar o Trojan (Alvo)
Configure o IP e a porta no arquivo .env que acompanha o `janus.py` e execute na máquina alvo:

```bash
python3 janus.py
```
---
Importante: 

- Não suba esse código para o vírus total nem plataformas semelhantes;
- Não rode o trojan em sua própria máquina (Por mais que o mesmo seja inofensivo ele possui persistência e ficará alocado nos registros do Windows consumindo memória até que você o tire de lá, e não adianta reiniciar a máquina);
- Para testes reais, o ideal é tornar o trojan (a parte que roda no alvo) em executável do Windows;
- Esse é meu primeiro malware, aceito críticas e sugestões de melhoria;
---

⚠️ Aviso Legal

Este software foi criado exclusivamente para fins educacionais e estudos de segurança defensiva/ofensiva. O uso desta ferramenta para acessar sistemas sem autorização prévia é ilegal e antiético. Este autor não se responsabiliza pelo uso indevido do mesmo.

📄 Licença

Este projeto está sob a licença MIT.
