# Chimera — Deployment: BYOC y Managed en AWS

> **Estado: REFERENCIA FASE 2 — no se construye este mes.** El código actual solo debe **no
> impedir** este diseño (data plane autocontenido, config externa, imágenes Docker por
> deployable). Movido aquí desde el plan maestro del proyecto (antes su §7) durante la
> consolidación documental de semana 1 — ver [`README.md`](README.md) para el índice de
> autoridad.

## El modelo mental: dos planos (y cómo lo hacen los referentes)

- **Control plane** (cuenta AWS de Chimera): cuentas/orgs de clientes, licencias, catálogo de versiones/distribuciones, provisioning, billing/metering, telemetría agregada, consola de administración. **Nunca datos del cliente** (ADR-019/PR3).
- **Data plane** (el Engine completo: gateway, runtime, capabilities, event store, anchors, Studio): en la cuenta del cliente (Modo B) o en la nuestra (Modo C). El self-host (Modo A) ES el data plane sin control plane — mismo artefacto.

| Referente          | Patrón                                                                                                                                                                                                                                                 | Qué copiar                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| **Databricks**     | Control plane en su cuenta; data plane (clusters) en la cuenta AWS del cliente vía cross-account IAM role; "secure cluster connectivity" = el data plane abre conexión **saliente** al control plane (cero puertos entrantes en la cuenta del cliente) | El modelo BYOC completo y el túnel outbound-only                                     |
| **Supabase**       | Managed: cada proyecto = stack dedicado (cómputo + Postgres propio) orquestado por su control plane; su self-host = el data plane completo en docker compose                                                                                           | Aislamiento por tenant como unidad de stack; self-host = mismo artefacto que managed |
| **Temporal Cloud** | Control plane global + "cells" de data plane aisladas; clientes conectan por gRPC + mTLS; namespace = unidad de tenancy; el OSS = self-host completo                                                                                                   | La conexión mTLS y el escalonamiento por celdas                                      |

## Mapeo a Chimera en AWS

**Modo A — self-host (ya es el demo del hackathon):** docker compose hoy, Helm chart después. Sin control plane. Licencia offline opcional.

**Modo B — BYOC (control plane de Chimera + data plane en cuenta del cliente):**

- El cliente instala el data plane en SU cuenta con un template publicado por nosotros (Terraform/CloudFormation): ECS/EKS + RDS Postgres + colas + Studio.
- Un **agente de data plane** (proceso pequeño) abre conexión saliente HTTPS/gRPC + mTLS al control plane: baja config/licencias/versiones, sube salud y métricas agregadas. **Sin puertos entrantes; sin contenido del cliente** — estructuralmente idéntico a lo que Inv-E/PR3 ya exigen.
- Variante enterprise (estilo Databricks): cross-account IAM role para que el control plane orqueste infra en la cuenta del cliente. Más potente, más fricción de confianza — segunda iteración, no la primera.
- Opcional: AWS PrivateLink para clientes que no aceptan tráfico por internet público.

**Modo C — managed total (Chimera provee control plane y data plane):**

- **Aislamiento por tenant = stack dedicado** (estilo Supabase): por tenant, servicios ECS Fargate (engine-api; capabilities pesadas como servicios o AWS Batch jobs), RDS Postgres, SQS/Redis, Secrets Manager, ALB + WAF; Studio estático en S3 + CloudFront. **Evitar multi-tenancy compartida dentro del engine al inicio**: multiplica complejidad y contradice el pitch de soberanía.
- **AWS Organizations**: cuenta de control plane, cuenta(s) de data planes, cuenta de build/ECR compartida. Landing zone (Control Tower) cuando crezca.
- El control plane en sí es una app normal (ECS + RDS + IdP) + un **provisioning worker** (Terraform/CDK automatizado) que crea/destruye stacks por tenant + metering para billing (p.ej. OpenMeter, del mapa de repos).
- GPU: Fargate no soporta GPU → serving local de modelos en cloud requiere EC2/EKS con nodos GPU, o modelo por API. QPU siempre es API externa (IBM/D-Wave) = "ejecución externa autorizada", igual en todos los modos.

## El orden de construcción (importa)

1. **Fase 2a — "hosted single-tenant" manual:** un script Terraform que levanta un stack Modo C por cliente, operado a mano. Consigue los primeros clientes managed **sin** construir control plane. (Así empezaron los referentes.)
2. **Fase 2b — control plane v0:** registro de tenants + provisioning automatizado + metering/billing.
3. **Fase 2c — Modo B (BYOC):** agente outbound-only + template de instalación en cuenta del cliente. Va al final aunque parezca "intermedio": BYOC es lo más caro de operar y soportar; se justifica cuando hay demanda enterprise real.

**Lo único que el código de este mes debe garantizar** (todo ya está en el plan): el data plane funciona 100% sin control plane (el Modo A lo prueba a diario); toda config entra por variables/manifiestos; una imagen Docker por deployable; telemetría agregada, opcional y saliente. B y C no agregan trabajo al mes del hackathon.
