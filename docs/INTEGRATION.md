# Reutilização em um projeto separado de imagens e PDFs

O Compress Image permanece independente. Uma aplicação que reúna este projeto e o Compress PDF será desenvolvida em um repositório separado; estas notas apenas descrevem o reaproveitamento possível. Nenhuma integração é executada aqui.

## Contratos dos motores

O Compress PDF consultado usa `compress_pdf(input_path, output_path, preset="ebook", *, overwrite=False, cancel_event=None, timeout=300)`. Aqui, a chamada é:

```python
compress_image(
    input_path,
    output_path,
    preset="balanced",
    *,
    settings=None,       # ImageSettings substitui as configurações do perfil
    overwrite=False,
    cancel_event=None,
    progress=None,       # callback(percentual, mensagem); executado na thread chamadora
)
```

Ambos os resultados expõem:

| Campo ou propriedade | Significado |
|---|---|
| `input_path`, `output_path` | Caminhos absolutos como `Path` |
| `original_size`, `compressed_size` | Tamanhos em bytes |
| `elapsed_seconds` | Tempo decorrido |
| `saved_bytes` | Original menos resultado; pode ser negativo em conversões de imagens |
| `reduction_percent` | Percentual de redução |

`ImageCompressionResult` estende o resultado com `width`, `height`, `format`, `quality`, `kept_original` e `notes`. A qualidade é `None` quando não se aplica ou quando os bytes originais foram mantidos.

Os erros têm nomes equivalentes (`CompressionError` e `CompressionCancelled`), mas são classes distintas nos dois repositórios. Ao unificar, faça os dois motores importarem essas classes de um módulo comum, ou capture explicitamente as duas classes em um adaptador. Apenas ter o mesmo nome não torna as classes intercambiáveis.

O cancelamento de imagens é cooperativo, entre etapas de leitura/codificação/gravação. O projeto PDF usa um processo separado, permitindo interromper chamadas nativas. Preserve essa diferença; não compartilhe documentos PyMuPDF entre threads.

## Incorporar o painel de imagens

`ImageCompressorFrame(master)` não cria uma janela nem inicia um loop gráfico. Por exemplo:

```python
import customtkinter as ctk
from image_gui import ImageCompressorFrame

ctk.set_appearance_mode("dark")
root = ctk.CTk()
root.geometry("1280x880")
root.minsize(1060, 760)

tabs = ctk.CTkTabview(root)
tabs.pack(fill="both", expand=True)
images_tab = tabs.add("Imagens")
images = ImageCompressorFrame(images_tab)
images.pack(fill="both", expand=True)

# Uma segunda aba pode receber o painel PDF após ele ser extraído.
root.protocol("WM_DELETE_WINDOW", images.close)
root.mainloop()
```

`images.add_paths(caminhos)` adiciona imagens sem diálogo. Destruir o painel cancela o processamento e remove seus callbacks. `images.close()` espera o cancelamento cooperativo se houver trabalho ativo e depois fecha a janela que o contém.

Em uma suíte com vários motores, o controlador da janela deve coordenar o fechamento de todos os painéis. Não conecte o fechamento somente ao painel de imagens se também houver PDFs em processamento.

## Próximos passos no projeto PDF

1. Extrair o conteúdo de `PDFCompressorApp` para um Frame que receba `master`. A implementação atual configura a janela e o protocolo de fechamento; apenas passá-la a uma aba não basta.
2. Adicionar os dois painéis a uma única janela com abas **Imagens** e **PDFs**.
3. Centralizar os contratos de resultado/erro e as funções de formatação de tamanhos e nomes de saída.
4. Manter os perfis de cada formato: qualidade e pixels para imagens; DPI e otimização estrutural para PDFs.
5. Reunir as dependências e ajustar o empacotamento. Validar separadamente a distribuição do PyMuPDF, que possui termos próprios.
6. Executar as regressões dos dois projetos e testar fechamento/cancelamento com as duas filas ativas.

Os arquivos existentes no repositório Compress PDF permanecem independentes. Esta alteração entrega a preparação do lado das imagens; não adiciona uma aba PDF sem um motor integrado.
