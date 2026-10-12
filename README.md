# Vitalia · Turnos de laboratorio

Prototipo para gestionar aclaraciones y atención en un laboratorio clínico. Incluye API Python con SQLite y cliente Angular. El paciente obtiene su folio con un toque, sin capturar datos personales.

## Arranque de la API

Requiere Python 3.10 o posterior. Desde la carpeta del proyecto:

```powershell
py -m backend.server
```

La API queda en `http://localhost:8000`. La primera ejecución crea `backend/turnos.db` automáticamente. No necesita paquetes externos. Al crear un folio, la API asigna automáticamente la siguiente mesa libre.

## Arranque de Angular

En otra terminal:

```powershell
cd frontend
npm install
npm start
```

Abre `http://localhost:4200`. Angular envía las solicitudes a la API en el puerto 8000.

## Funciones

- Toma de turno con folio automático, sin nombre ni número de tarjeta.
- Asignación automática a una de cuatro mesas libres.
- Cada atención de demostración termina sola a los 30 segundos y la mesa recibe el siguiente folio.
- La interfaz se actualiza cada 2.5 segundos; al activar la campanita, suena cuando llega un turno nuevo a una mesa.
- El menú permite saltar directamente entre Turnos y Atención.
- Tablero público con turnos esperando, mesa y código del paciente.
- SQLite local para conservar turnos al reiniciar el servidor.

## Rutas principales

- `GET /api/state`: resumen de mesas y cola.
- `POST /api/tickets`: genera un folio sin datos personales.
- `TICKET_DURATION_SECONDS`: variable opcional para cambiar la duración automática de atención (por defecto `30`).

## Nota

Es una base demostrativa: antes de manejar datos reales de pacientes se requiere autenticación, controles de acceso, política de privacidad, auditoría y despliegue seguro. No recopila resultados clínicos.
# Despliegue en Vercel

El repositorio debe importarse desde su carpeta raíz (la carpeta que contiene `vercel.json`). En Vercel configura:

- **Root Directory:** `.` (la raíz del repositorio, no `frontend`).
- **Framework Preset:** `Other`.
- **Build Command:** `npm run build`.
- **Output Directory:** `frontend/dist/vitalia/browser`.
- **Install Command:** se puede dejar el valor predeterminado; el comando de build instala las dependencias de Angular.
- **Environment Variable:** `DATABASE_URL`, con la cadena de conexión PostgreSQL de una base de datos Neon.

Las funciones Python viven en `api/` y guardan los turnos en PostgreSQL. No uses SQLite en Vercel: el disco de una función no es almacenamiento persistente. La API local (`py -m backend.server`) conserva SQLite para desarrollo.

Al crear la base de datos Neon, copia la cadena de conexión PostgreSQL y guárdala como `DATABASE_URL` en **Project Settings → Environment Variables** de Vercel. No publiques esa cadena ni la agregues al repositorio.

Después de desplegar, abre `/api/state` en el dominio asignado para confirmar que la API responde. Si aparece `Falta configurar DATABASE_URL`, agrega la variable y vuelve a desplegar.
