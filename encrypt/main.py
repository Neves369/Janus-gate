import os
import inquirer
from modules import stringObfuscation


def main():

  os.system('cls')

  # print("""
  #    ____________________________________________________________________
  #   |--------------------------------------------------------------------|
  #   |      ██╗    ███████████╗     ██████╗██████╗███╗   ██████████╗      |
  #   |      ██║    ████╔════██║    ██╔════██╔═══██████╗ ██████╔════╝      |
  #   |      ██║ █╗ ███████╗ ██║    ██║    ██║   ████╔████╔███████╗        |
  #   |      ██║███╗████╔══╝ ██║    ██║    ██║   ████║╚██╔╝████╔══╝        |
  #   |      ╚███╔███╔██████████████╚██████╚██████╔██║ ╚═╝ █████████╗      |
  #   |       ╚══╝╚══╝╚══════╚══════╝╚═════╝╚═════╝╚═╝     ╚═╚══════╝      |
  #   |                                                                    |
  #   |--------------------------OFUSCAR STRING----------------------------|
  #   |--Informe a string                                                  |
  #   |--Selecione o tipo de ofuscacao                                     |
  #   |--Copie o resultado                                                 |
  #   |--------------------------------------------------------------------|
  #   |____________________________________________________________________| 
  # """) 

  # Seletor de operação: Encriptar (texto -> hex) ou Decifrar (hex -> texto).
  # inquirer.List renderiza um menu navegável no terminal.
  operation = inquirer.prompt([
    inquirer.List(
      'operation',
      message="Escolha a operacao",
      choices=['Encriptar', 'Decifrar'],
    ),
  ])["operation"]

  # --- ENCRIPTAR: texto + chave -> hex --------------------------------------
  if operation == 'Encriptar':
    questions = [
      inquirer.Text(
        'string',
        message="Informe a String",
      ),
      inquirer.Text(
          'key',
          message="Informe a Chave",
      ),
    ]
    answers = inquirer.prompt(questions)

    result = stringObfuscation.encrypt_string(answers["string"], answers["key"])

    print("""
  -------------------------------------------------------------------

   ██████╗██████╗███╗   █████████╗██╗    ██████████████████████╗
  ██╔════██╔═══██████╗ ██████╔══████║    ██╔════╚══██╔══██╔════╝
  ██║    ██║   ████╔████╔████████╔██║    █████╗    ██║  █████╗  
  ██║    ██║   ████║╚██╔╝████╔═══╝██║    ██╔══╝    ██║  ██╔══╝  
  ╚██████╚██████╔██║ ╚═╝ ████║    ██████████████╗  ██║  ███████╗
  ╚═════╝╚═════╝╚═╝     ╚═╚═╝    ╚══════╚══════╝  ╚═╝  ╚══════╝

  --------------------STRING ENCRIPTADA (HEX):----------------------
  """) 
    print(result)

    # Round-trip: confirma que o hex gerado volta ao texto original com a
    # mesma chave (XOR é simétrico). Erro aqui = a string/chave geraram um
    # bytecode que não é UTF-8 válido (provável com acentos/emojis).
    try:
      plain = stringObfuscation.decrypt_string(result, answers["key"])
      print("\n[i] Round-trip (decifrar com a mesma chave):", plain)
    except UnicodeDecodeError:
      print("[-] Round-trip nao exibido: chave/string geram texto invalido")

  # --- DECIFRAR: hex + chave -> texto ---------------------------------------
  else:  # Decifrar
    questions = [
      inquirer.Text(
        'cipher',
        message="Informe o HEX",
      ),
      inquirer.Text(
          'key',
          message="Informe a Chave",
      ),
    ]
    answers = inquirer.prompt(questions)

    try:
      plain = stringObfuscation.decrypt_string(answers["cipher"], answers["key"])

      print("""
  -------------------------------------------------------------------

   ██████╗██████╗███╗   █████████╗██╗    ██████████████████████╗
  ██╔════██╔═══██████╗ ██████╔══████║    ██╔════╚══██╔══██╔════╝
  ██║    ██║   ████╔████╔████████╔██║    █████╗    ██║  █████╗  
  ██║    ██║   ████║╚██╔╝████╔═══╝██║    ██╔══╝    ██║  ██╔══╝  
  ╚██████╚██████╔██║ ╚═╝ ████║    ██████████████╗  ██║  ███████╗
  ╚═════╝╚═════╝╚═╝     ╚═╚═╝    ╚══════╚══════╝  ╚═╝  ╚══════╝

  --------------------STRING DECIFRADA:------------------------------
  """) 
      print(plain)

      # Validação reversa: re-encripta o texto obtido e confere se o hex bate.
      # Se não bater, a chave está errada ou o hex foi digitado/copiado errado.
      validation = stringObfuscation.encrypt_string(plain, answers["key"])
      if validation.lower() == answers["cipher"].lower():
        print("\n[+] Validacao ok: re-encriptado bate com o hex digitado")
      else:
        print("\n[-] Atencao: re-encriptado NAO bateu (chave errada ou dados corrompidos)")

    except ValueError:
      # ValueError: bytes.fromhex falhou (hex malformado)
      print("\n[-] Entrada HEX invalida")
    except UnicodeDecodeError:
      # UnicodeDecodeError: chave errada decodificou bytecode inválido
      print("\n[-] Nao foi possivel decifrar (chave errada ou dados corrompidos)")

  # Confirmação de saída; default True para encerrar sem digitar mais nada.
  confirm = {
    inquirer.Confirm(
      'confirmed',
      message="Deseja sair?" ,
      default=True),
  }
  confirmation = inquirer.prompt(confirm)

  if(confirmation["confirmed"]):
    quit()


if __name__ == '__main__':
  while True:
    main()