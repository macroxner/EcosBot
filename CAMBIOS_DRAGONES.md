# EcosBot — integración de Dragones

## Crear una actividad

```text
?dragon 03/09/2026 20:00 22:00
```

Alias: `?dragones`.

El bot calcula automáticamente la hora UTC a partir de `Europe/Madrid`, crea el hilo y mantiene la composición.

## Apuntarse en el hilo

Siempre hay que escribir `x` delante:

- `x mangual`
- `x incubo`
- `x maracas`
- `x monarca`
- `x rompe`
- `x mh` / `x healer`
- `x healer 2` / `x helaer 2`
- `x rdps` / `x ir dps`
- `x sc`
- `x lc` / `x pajaro` / `x lightcaller`
- `x fuego` / `x fire` / `x flami`
- `x ballesta` / `x repetidora` / `x wailing`
- `x dps` para el primer DPS libre

También se puede apuntar a otra persona: `x mangual @usuario`.

Fill funciona igual que en Avas: `x fill`, `x fill menos healer`, `x fill menos dps @usuario`.

Para salir: `signoff` o `signoff @usuario`.

## Comandos nuevos

- `?dragoncalendar` / `?dcalendar`
- `?dragonstats [@usuario]` / `?dstats`
- `?dragontop` / `?dtop`
- `?dragoninactive [dias]` / `?dinactive [dias]`

El calendario automático de Dragones se publica en `CALENDAR_CHANNEL` y el control de inactividad de 14 días en `INACTIVE_CHANNEL`, usando mensajes independientes de los de Avalonianas.

## Integraciones

- `?dashboard` tiene pestaña de Dragones.
- `?stats` incluye Dragones.
- `?profile` incluye Dragones.
- `?achievements` incluye logros de 10, 50 y 100 Dragones y otorga roles automáticamente.
- Todos los mensajes visibles de los comandos se han migrado a embeds.


## Ajuste de composición v3
- Los dos Juradores aparecen juntos.
- DPS 1-5 son las posiciones de ballesta/ranged DPS.
- DPS 6 es Lightcaller.
- DPS 7 es Flamígero/Fuego.
- Al crear un Dragón, el hilo menciona automáticamente los IDs 1338207294579539991, 1332749148000227369 y 1540712364452610178.
- El hilo adjunta `assets/dragon_compo.png` con la tabla de builds aportada.

## v8
- Nueva composición de Dragones de 20 huecos: Main Tank, 2 Offtank, Main Healer, 2 Healer Party 1, 2 Healer Party 2, Invocador Oscuro, 2 Enigmáticos y 9 DPS.
- Nuevos alias de inscripción para Dragones, manteniendo `x` obligatorio.
- DPS especializados se muestran como DPS Ballesta, DPS Flami o DPS Pajaro; `x dps` ocupa cualquier DPS libre.
- EcoShop: mute pasa a 2 minutos; roles temporales y cambio de nick pasan a 30 minutos, sin modificar precios.
