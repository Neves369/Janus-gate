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

  operation = inquirer.prompt([
    inquirer.List(
      'operation',
      message="Escolha a operacao",
      choices=['Encriptar', 'Decifrar'],
    ),
  ])["operation"]

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

    try:
      plain = stringObfuscation.decrypt_string(result, answers["key"])
      print("\n[i] Round-trip (decifrar com a mesma chave):", plain)
    except UnicodeDecodeError:
      print("[-] Round-trip nao exibido: chave/string geram texto invalido")

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

      validation = stringObfuscation.encrypt_string(plain, answers["key"])
      if validation.lower() == answers["cipher"].lower():
        print("\n[+] Validacao ok: re-encriptado bate com o hex digitado")
      else:
        print("\n[-] Atencao: re-encriptado NAO bateu (chave errada ou dados corrompidos)")

    except ValueError:
      print("\n[-] Entrada HEX invalida")
    except UnicodeDecodeError:
      print("\n[-] Nao foi possivel decifrar (chave errada ou dados corrompidos)")

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