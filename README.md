# Coderhouse Data Platform — Infraestructura Base

**Pre-entrega 1: Infraestructura Base con Entorno de Desarrollo e IAM Core**

## Descripción

Implementación de una infraestructura base para una plataforma de datos en AWS utilizando Terraform e Infrastructure as Code (IaC).

El proyecto establece los componentes de red, almacenamiento de estado remoto e identidad necesarios para futuras integraciones de procesamiento de datos mediante AWS Lambda, Amazon Kinesis y Apache Flink.

## Arquitectura

- **Terraform Backend:** Amazon S3 con cifrado SSE-S3 y versionado.
- **State Locking:** Amazon DynamoDB.
- **Networking:** VPC con dos subredes privadas en diferentes zonas de disponibilidad.
- **S3 Gateway Endpoint:** acceso a Amazon S3 desde las subredes privadas sin utilizar NAT Gateway.
- **IAM:** roles independientes para procesamiento de datos y auditoría.
- **Data Lake:** bucket S3 independiente del almacenamiento de estado de Terraform.

## Estructura del proyecto

```text
coderhouse-data-platform/
├── bootstrap/
│   └── bootstrap.ps1
├── modules/
│   ├── network/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── versions.tf
│   └── identity/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── versions.tf
├── environments/
│   └── dev/
│       ├── backend.tf
│       ├── providers.tf
│       ├── variables.tf
│       ├── main.tf
│       ├── storage.tf
│       ├── outputs.tf
│       └── .terraform.lock.hcl
├── .gitignore
├── PLAN_OUTPUT.md
└── README.md
```

## Requisitos

- Terraform 1.10 o superior.
- AWS CLI v2.
- Git.
- Cuenta AWS con permisos para administrar los recursos del proyecto.
- TFLint (recomendado).

## Configuración

La infraestructura utiliza la región `us-east-1` y el entorno `dev`.

El perfil local de AWS CLI se configura mediante:

```powershell
aws configure --profile coderhouse-dev
```

Verificación de identidad:

```powershell
aws sts get-caller-identity --profile coderhouse-dev
```

Las credenciales deben mantenerse fuera del repositorio.

## Backend remoto

El backend se almacena en:

- Bucket: `coderhouse-terraform-672049777597`
- Estado: `environments/dev/terraform.tfstate`
- Tabla DynamoDB: `coderhouse-terraform-locks`

El bucket utiliza cifrado SSE-S3, versionado y bloqueo de acceso público.

La tabla DynamoDB utiliza la clave de partición `LockID` y el modo `PAY_PER_REQUEST`.

**Nota:** el locking mediante DynamoDB está deprecado en Terraform, pero se mantiene para cumplir los requisitos del ejercicio. Para nuevas implementaciones se recomienda evaluar el locking nativo de S3.

Los recursos del backend deben crearse antes de inicializar Terraform. El directorio `bootstrap/` contiene el script de referencia; debe verificarse la existencia de los recursos antes de ejecutarlo para evitar conflictos.

## Infraestructura de red

La VPC utiliza el rango `10.10.0.0/16`.

| Recurso | Configuración |
|---|---|
| VPC | `10.10.0.0/16` |
| Subred privada 1 | `10.10.1.0/24` |
| Subred privada 2 | `10.10.2.0/24` |
| Tablas de rutas | Una por subred privada |
| Endpoint S3 | Gateway |
| NAT Gateway | No implementado |
| Internet Gateway | No implementado |

Las tablas de rutas privadas contienen rutas locales y una ruta hacia S3 mediante el Gateway Endpoint.

No se configuran rutas predeterminadas hacia internet.

## Seguridad e identidad

### Rol de procesamiento

`coderhouse-dev-processing`

Permite las siguientes operaciones:

- `s3:ListBucket`, limitado al prefijo `raw/`.
- `s3:GetObject`, sobre objetos dentro de `raw/`.
- `s3:PutObject`, sobre objetos dentro de `raw/`.

Bucket autorizado: `coderhouse-data-lake-672049777597`.

El rol está preparado como base para servicios Lambda y Flink. Los permisos adicionales requeridos para ejecución, logging o consumo de Kinesis se incorporarán en futuras etapas.

### Rol de auditoría

`coderhouse-dev-audit`

Permite consultar información de VPC, subredes, tablas de rutas, endpoints y metadatos seleccionados del Data Lake.

No incluye acciones de modificación de infraestructura.

## Despliegue

Desde el directorio `environments/dev`:

```powershell
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
terraform apply
```

Para consultar los identificadores de los recursos:

```powershell
terraform output
```

Para verificar diferencias posteriores:

```powershell
terraform plan
```

## Validaciones

La infraestructura fue desplegada y verificada mediante AWS CLI y Terraform.

Se comprobaron:

- Existencia de VPC y subredes privadas.
- Asociación del S3 Gateway Endpoint a ambas tablas de rutas privadas.
- Ausencia de rutas predeterminadas hacia internet.
- Políticas IAM limitadas según la función de cada rol.
- Estado remoto configurado en S3.
- Análisis estático mediante Terraform Validate y TFLint.
- Ausencia de diferencias entre el código y la infraestructura desplegada.

Resultado final de Terraform:

```text
No changes. Your infrastructure matches the configuration.
```

## Próximas etapas

La infraestructura permitirá incorporar servicios de ingesta, procesamiento y almacenamiento de datos mediante AWS Kinesis, AWS Lambda y Apache Flink.

## Consideraciones de costos

Se evita la creación de instancias EC2 y NAT Gateways. El S3 Gateway Endpoint no tiene cargo por hora.

El uso de S3, DynamoDB y otros servicios puede generar cargos según consumo. Se recomienda configurar alertas mediante AWS Budgets.

## Autor

Proyecto académico — Coderhouse, Data Engineering.
