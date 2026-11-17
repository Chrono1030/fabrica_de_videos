# Contrato de metadatos

`fabrica.metadata.PublicationPackage`: Pydantic cerrado a campos desconocidos,
privacidad exclusivamente `private`, plataforma YouTube, marca Mente y Capital,
es-419. Incluye job_id, hash de video y guion, título, descripción, hashtags, tags,
categoría editorial y category_id, público y su motivo, indicador de medios
sintéticos y motivo, portada, fuentes, recursos/licencias, ficha de originalidad.

`generate_package` recibe el guion Pydantic ya validado, datos editoriales,
duración medida, recursos y decisiones de público/declaración. El MOCK conserva
el título del guion y extrae su gancho, introducción y cierre: no inventa beneficios,
citas ni fuentes, ni agrega promesas para intentar mejorar clics. Títulos hasta
100 caracteres, descripciones hasta 5000, hashtags limitados y sin duplicados.
La SQLite rechaza títulos/descripciones normalizados repetidos o con similitud
textual determinista >= 0.90 en distintos jobs. No es un clasificador semántico.
La regeneración idéntica de un mismo job es idempotente; no reemplaza paquetes
reservados con contenido distinto. No se usa una API de pago.

`validate_correspondence` liga el hash del guion y sus fuentes al paquete, comprueba
título y contenido extractivo. El publicador además vuelve a validar Pydantic y
comprueba bytes de recursos y video, duración, archivo de portada y QA técnico.
Esto no constituye una verificación semántica de cualquier texto arbitrario.

`made_for_kids` y `contains_synthetic_media` son decisiones explícitas por video;
la edad de la audiencia y tener TTS no bastan para decidir automáticamente.
Los ejemplos marcan público adulto y ausencia de representación realista solo
para sus gráficos y tonos MOCK, conservando motivo y revisión pendiente.

Se reutilizan Pydantic y SQLite existentes. No hace falta instalar otra aplicación
para metadatos. Se evaluaron las opciones del OPEN_SOURCE_REUSE_PLAN del PR 2:
MoneyPrinterTurbo/ShortGPT no ofrecen beneficio que justifique incorporar otro
pipeline; no se copió su código. La descripción determinista es una base
extractiva, sin promesa de optimización SEO validada con audiencia.

El category_id `27` es una **fixture educativa** del simulador. Antes de OAuth
real se deberá validar disponibilidad/región con `videoCategories.list`, además
de idioma, público y divulgación. La portada es un fotograma ya renderizado;
no se afirma haberla cargado ni verificado aceptación remota como miniatura.
