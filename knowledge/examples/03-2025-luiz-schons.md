Titulo: Do erro ao acerto: CORS - Descomplicando um dos maiores pesadelos do frontend
Subtitulo: Aprenda a decifrar os misteriosos erros de CORS que aparecem no navegador mas não no Postman, e eleve seu conhecimento técnico para o próximo nível! 💡

Fala GDG! **Batemos recorde de público!**

O [DevParaná na Estrada](https://linktr.ee/developerparana) agitou o [Auditório da Unopar Anhanguera - Catuaí](https://maps.app.goo.gl/4z4dwUZgYypGWQbo9) com mais de **150 participantes**. O auditório lotado mostrou que nossa comunidade está mais forte do que nunca.

Foi incrível ver tantos rostos novos se misturando com os participantes de longa data, criando aquela energia contagiante que só acontece quando devs se reúnem para aprender juntos.

Tivemos duas palestras excepcionais:

[**Luiz Schons**](https://www.linkedin.com/in/luiz-schons/) abriu o evento com o tema **"CORS: No Postman funciona!"** — desvendando um dos mistérios mais comuns do desenvolvimento web.

E [**Enrico Secco**](https://www.linkedin.com/in/enrico-secco) encerrou com **"Decisões técnicas com impacto estratégico: React Query e Next.js no cache de projetos frontend reais"**.

Muito obrigado a todos que compareceram, fizeram perguntas e aproveitaram para expandir o networking com outros devs!

[

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdb6d35b7-f1d7-4484-8e82-07c8143c854d_3008x2000.jpeg)



](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdb6d35b7-f1d7-4484-8e82-07c8143c854d_3008x2000.jpeg)

Nesta edição, vamos explorar os principais insights da palestra do Luiz e entender **por que seu código funciona no Postman mas falha no navegador** — um problema que afeta praticamente todo desenvolvedor web em algum momento.

E na próxima edição: **React Query e Next.js!** Como decisões técnicas sobre cache podem impactar estrategicamente seus projetos frontend? Vamos explorar esse tema na próxima newsletter!

**Não perca!** Se inscreva na nossa newsletter para ficar por dentro das próximas edições.

## Já interagiu com a comunidade hoje?

A cada evento, nossa comunidade só cresce, e o engajamento aumenta! Se você está aqui, já faz parte desse grupo incrível que agora reúne **mais de 1000 inscritos** 🎉 — acabamos de atingir esse marco incrível graças à participação e ao apoio contínuo de todos vocês! Por isso, não deixe de acompanhar e fazer parte dessa jornada com a gente. No nosso site, você encontra diversas formas de interagir e se conectar com outros desenvolvedores. 👉 [https://gdg.londrina.dev](https://gdg.londrina.dev)

E não para por aí! Nossa **comunidade no WhatsApp** é o lugar perfeito para ficar por dentro dos próximos eventos, trocar ideias, participar de discussões sobre tecnologia, rir com memes e, claro, se manter atualizado sobre vagas para todos os níveis e stacks. É a maneira mais prática de estar sempre conectado com a galera da **comunidade Dev de Londrina e região!**

Conecte-se com a gente [clicando aqui](https://chat.whatsapp.com/GVZ5UFI6ZjBE6dVDwNcoSF).

---

Agora vamos ao que interessa!

[

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F16319312-7843-42ea-8b7e-07b7ebb3a7e4_3008x2000.jpeg)



](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F16319312-7843-42ea-8b7e-07b7ebb3a7e4_3008x2000.jpeg)

## 🎯 CORS: No Postman funciona! (Mas no navegador não...)

Você já passou por aquela situação frustrante? **Seu código funciona perfeitamente no Postman**, mas quando tenta executar a mesma requisição no navegador, aparece um erro misterioso mencionando "CORS". O Luiz Schons desvendou esse mistério que aparece em **quase toda entrevista de emprego para desenvolvedores frontend**.

### **📌 O que é CORS e por que ele existe?**

CORS (Cross-Origin Resource Sharing) é um mecanismo de segurança implementado pelos navegadores — e não pelas APIs! Essa é a primeira confusão que o Luiz esclareceu.

> "O CORS existe para proteger os usuários, não as aplicações."

Quando você acessa um site, o navegador impõe uma regra chamada "Same Origin Policy" (Política de Mesma Origem). Simplificando: por padrão, seu código JavaScript só pode fazer requisições para o mesmo domínio de onde foi carregado.

**Por exemplo:**

- Se seu site é `meuapp.com`, ele pode naturalmente fazer requisições para `meuapp.com/api`
    
- Mas se tentar acessar `outroservico.com/api`, o navegador vai bloquear... a menos que o servidor de destino permita explicitamente
    

### **🛠️ Por que no Postman funciona?**

A diferença fundamental é que o **Postman não é um navegador**! Ele não implementa as restrições de CORS — assim como aplicativos desktop, mobile ou scripts rodando diretamente no terminal.

Durante a demonstração ao vivo, Luiz mostrou exatamente isso:

1. Uma requisição que funcionou perfeitamente via linha de comando
    
2. A mesma requisição falhando no navegador com erro de CORS
    

O erro de CORS geralmente aponta para um destes três problemas:

- **ORIGIN**: O servidor não permite requisições do seu domínio
    
- **METHOD**: O método HTTP não é permitido (PUT, DELETE, etc.)
    
- **HEADERS**: Algum header personalizado não é permitido
    

Outro conceito importante: antes de enviar alguns tipos de requisições, o navegador faz uma "pergunta prévia" ao servidor usando o método HTTP OPTIONS. Essa requisição prévia é chamada de "_preflight_" e acontece automaticamente.

> #### O que são requisições "preflight"?
> 
> Quando você faz certos tipos de requisições HTTP (especialmente as "não-simples" como PUT, DELETE, ou com headers customizados), o navegador envia automaticamente uma requisição preliminar usando o método OPTIONS. É como se o navegador perguntasse educadamente ao servidor: "Posso fazer esta requisição especial?".
> 
> Esta verificação prévia se chama "preflight" e funciona assim:
> 
> 1. O navegador envia um OPTIONS para o servidor
>     
> 2. O servidor responde com headers que definem o que é permitido
>     
> 3. Se aprovado, o navegador envia a requisição original
>     
> 4. Se negado, o navegador bloqueia a requisição com erro de CORS
>     

Tudo isso acontece nos bastidores, e você só percebe quando algo dá errado. Curiosamente, requisições simples usando GET, POST e HEAD são "parcialmente isentas" das restrições de CORS.

Por que essa exceção? Por compatibilidade com a web antiga! Quando as regras de CORS foram criadas, a maioria dos sites usava apenas GET e POST, e exigir conformidade total quebraria boa parte da internet da época.

[

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0f5142a0-b19d-42e2-97f2-a6758718b1f6_3008x2000.jpeg)



](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0f5142a0-b19d-42e2-97f2-a6758718b1f6_3008x2000.jpeg)

### Como resolver problemas de CORS na prática

Na maioria dos casos, a solução está do lado do servidor, não do seu código frontend. O servidor precisa adicionar os headers corretos para permitir requisições cross-origin:

```
Access-Control-Allow-Origin: https://meuapp.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
```

Em ambientes de produção, essas configurações geralmente ficam em um API Gateway, não diretamente no seu código backend.

> #### O que é um API Gateway?
> 
> Um API Gateway é uma ferramenta especializada que gerencia o tráfego de APIs em arquiteturas modernas. Ele funciona como um ponto de entrada centralizado que não apenas encaminha requisições, mas também implementa funcionalidades específicas para o gerenciamento de APIs (rate limiting, autenticação e autorização, gerenciamento de CORS, monitoramento e analytics, etc.).

### Dicas práticas para seu dia a dia:

1. **Verifique se as origens estão corretas**: Pequenas diferenças como `http` vs `https` ou presença vs ausência de `www` podem causar problemas de CORS
    
2. **Atenção com portas no localhost**: `localhost:3000` e `localhost:8080` são considerados origens diferentes
    
3. **Leia o erro com atenção**: A mensagem de erro geralmente indica exatamente o que está faltando
    

Como o Luiz destacou ao final: "**O CORS é uma proteção para os usuários finais, não para sua aplicação.** Ele impede que sites maliciosos façam requisições usando seus cookies e credenciais sem sua permissão."

Entender CORS é um diferencial técnico importante que pode te ajudar tanto em entrevistas quanto no dia a dia. É um daqueles assuntos que parecem complicados à primeira vista, mas que fazem total sentido depois que você entende a lógica por trás.

---

## ⚡ React Query, Next.js e o poder do cache no frontend

E quando falamos de otimização de performance no frontend? 🤔

Na próxima newsletter, vamos explorar como o [Enrico Secco](https://www.linkedin.com/in/enrico-secco) compartilhou estratégias práticas sobre **decisões técnicas com impacto estratégico**, focando em como React Query e Next.js podem transformar a experiência do usuário com estratégias inteligentes de cache.

Vamos falar sobre **como decisões aparentemente técnicas podem ter impacto direto no negócio**, aumentando a retenção de usuários e otimizando recursos. Entender esses conceitos pode elevar seu nível como desenvolvedor frontend e trazer resultados tangíveis para seus projetos.

Fica de olho! 👀 **Se ainda não está inscrito na nossa newsletter, assine agora para receber direto no seu e-mail.**

## **Vem para a Comunidade!**

Ajudar pessoas a crescer na área de tecnologia é um dos nossos objetivos como comunidade. Cada evento é uma oportunidade de aprender, se conectar e até mesmo compartilhar o que você sabe. Que tal [dar uma palestra](https://docs.google.com/forms/d/e/1FAIpQLSd4gEpJj_806AhqdSiJhZa6qirafF4uYUs-Ika1PZffPFKsgg/viewform) no próximo encontro? A comunidade está aqui para te apoiar e incentivar.

Não deixe de acompanhar nossas novidades, interagir com o pessoal e aproveitar ao máximo tudo o que o **GDG Londrina** tem a oferecer. **Juntos, podemos transformar o cenário de tecnologia na região e no Brasil.** Bora lá? 🚀

[Faça parte da comunidade](https://gdg.londrina.dev/)