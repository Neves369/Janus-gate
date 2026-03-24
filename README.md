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

## 💻 Como Utilizar

### 1. Preparar o Listener (Seu terminal)
Configure o IP e a porta no arquivo `janus.py` e execute:

```bash
python3 janus.py


Importante: Não suba esse código para o vírus total nem plataformas semelhantes