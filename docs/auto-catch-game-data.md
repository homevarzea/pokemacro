# Auto Catch pelo nome do Pokémon

Na página Auto Catch, escolha **Game data** e conecte ao jogo. O Windows
pode pedir elevação para conectar ao PokeAlliance.

1. Em **Ball to use**, escolha a ball pelo nome.
2. Selecione os Pokémon e clique em **Start Auto Catch**.

O perfil inclui 13 tipos confirmados no jogo, incluindo Poké, Ultra, Dusk,
Fast, Heavy, Magu, Moon e Net. Para acrescentar outra ball, abra no jogo a
bolsa que contém suas balls vazias, clique em **Detect balls** e mantenha
a bolsa aberta até terminar.

A seleção é salva automaticamente. Para trocar a ball, pare o Auto Catch.
Você pode abrir outras bolsas e repetir a detecção para acrescentar tipos.
**Cancel detection** interrompe a consulta, e **Stop Auto Catch** interrompe
os lançamentos.

Em **Catch speed**, configure o intervalo entre balls de 100 a 3000 ms.
Os atalhos **Fast · 300 ms** e **Normal · 500 ms** preenchem o campo.
A configuração é salva automaticamente e aplicada ao iniciar. Pare o Auto
Catch antes de alterar a velocidade. O mapa é consultado a cada 100 ms;
o tempo de resposta do servidor também influencia a velocidade efetiva.

As balls adicionais são identificadas
pela descrição de **Empty ... Ball(s)** enviada pelo servidor: a quantidade
precisa corresponder à pilha consultada, e uma segunda consulta confirma
o nome. Balls com Pokémon e outros itens não entram na lista. A detecção
faz apenas Look, com pelo menos 500 ms entre consultas, sem lançar balls.
Ela exige que o Auto Catch esteja parado. O catálogo aprendido é salvo
localmente por versão do cliente e carregado nas próximas conexões.

Os IDs ficam internos. O uso aceita apenas uma ball reconhecida no catálogo,
com nome e ID correspondentes. Se a ball escolhida acabar, o Auto Catch para;
ele não troca automaticamente para outra ball.

O teste neste computador confirmou Gloom, Oddish e a Ultra Ball diretamente
pela descrição enviada pelo jogo. Uma Ultra Ball foi usada em um Gloom:
a contagem passou de 5792 para 5791 e o servidor informou que a ball quebrou.

A validação da seleção de balls consultou 40 tipos de item nas bolsas abertas
e reconheceu 13 tipos de ball. A troca temporária para Magu Ball retornou a
contagem correta de 54, e a seleção foi restaurada para Ultra Ball. Durante
essa validação, o Auto Catch permaneceu parado e nenhuma ball foi lançada.

Para outro Pokémon, adicione seu nome. O cliente identifica o corpse pela
flag `isLyingCorpse`, consulta sua descrição com `g_game.look` e guarda a
associação entre o nome e o ID. O filtro compara nomes sem distinguir
maiúsculas. Um tipo ainda sem nome não recebe balls.

A leitura usa tiles no mesmo andar, até sete tiles na horizontal e cinco
na vertical. O uso é feito por `g_game.useInventoryItemWith`, sem coordenadas
de mouse. Cada objeto de corpse recebe uma tentativa; corpos removidos
saem do registro para que novos corpos no mesmo tile possam ser usados.
O intervalo mínimo entre tentativas segue a configuração de velocidade.

O processo elevado aceita apenas operações fixas de iniciar, parar,
configurar, detectar/cancelar a detecção de balls e consultar o estado.
Ele encerra quando o Pokemacro fecha.
O cliente também para se ficar 12 segundos sem heartbeat, ao deslogar ou
quando não há balls.

Os testes de configuração e a simulação Lua verificam a seleção, a detecção
sem lançamentos, a exclusão de outros itens, a confirmação da descrição,
a parada por falta da ball escolhida e a prevenção de tentativas repetidas.

O `.exe` da release inclui Python, Frida e os scripts da ponte. Extraia o
ZIP e execute `pokemacro.exe`; não é necessário instalar Python, Frida ou
o projeto frida-decrypt. Apenas o processo da ponte solicita elevação.
As configurações e os catálogos pessoais ficam em `%APPDATA%/Pokemacro`.

Na execução Python do projeto, instale as dependências do Pipfile.lock.
O perfil Frida 17.17.0 é específico do
cliente x64 com SHA-256
`5db2cf3f15ae5e92ea6843a8a80011723146068b409dda930387521d123f6e33`.
O hash e os bytes das funções Lua são verificados antes da conexão.
O executável é localizado pelo processo aberto; o jogo pode estar instalado
em outra pasta. Abra apenas um cliente compatível antes de conectar.

O workflow valida os testes Python e executa `--bridge-self-test` no `.exe`
gerado antes de publicar. Essa verificação carrega a extensão nativa do
Frida e confere os recursos incluídos, sem conectar a um jogo. Ao conectar,
a ponte também executa a simulação Lua antes de habilitar o Auto Catch.

O modo **Image recognition** conserva a configuração anterior por imagens
e suas hotkeys.
