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
