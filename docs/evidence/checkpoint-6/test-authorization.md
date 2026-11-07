# Autorización de ensayo temporal

El propietario autorizó ejecutar únicamente la prueba y retirar después los
recursos temporales para evitar sus cargos. No autoriza eliminar infraestructura
de entregas anteriores. Se conserva Kinesis, Flink, Iceberg, Glue, S3 y la VPC.

Antes de crear recursos debe estar disponible también el acceso necesario para
eliminarlos. El 06/11/2026 se volvió a consultar ListWorkgroups y KMS DescribeKey:
ambos siguen denegados para terraform-dev. No se ejecutó apply ni se creó Redshift.

Política propuesta: `docs/redshift-test-operator-access.json`, para agregar como
política administrada al operador terraform-dev. Amplía los permisos observados
faltantes con creación, consultas y retiro de warehouses etiquetados Checkpoint=6
y Project=coderhouse-data-platform. Usage limits no admite restricción por ARN en
las operaciones utilizadas; se limita la región. No contiene administración IAM
global. Se apoya en los permisos Terraform de red/IAM existentes; cualquier otro
AccessDenied se resolverá específicamente, sin adjuntar AdministratorAccess.

Orden de trabajo tras habilitar accesos: inventario real; plan actualizado;
apply autorizado; bootstrap SQL; prueba única y evidencias; exportar resultados;
plan enable_redshift=false con enable_ingestion=true; verificar que todas las
bajas pertenezcan a module.redshift[0]; aplicar el retiro autorizado y confirmar
ausencia del workgroup, namespace y endpoint temporal. No crear snapshots de pago
sin necesidad; conservar las evidencias en Git antes del retiro.

Los recursos anteriores, especialmente Kinesis y S3, mantienen sus cargos.

## Segundo intento: permisos de inventario habilitados

El propietario agregó la política y confirmó su instalación. ListWorkgroups y
DescribeClusters devolvieron listas vacías y DescribeKey confirmó el ARN esperado.
El plan actualizado volvió a proponer 8 altas, 0 cambios y 0 bajas.

El apply autorizado se detuvo en CreateRole y CreateSecurityGroup por AccessDenied.
Ambas creaciones fallaron: no hay workgroups ni security groups temporales, y el
estado solo contiene los dos data sources del módulo, sin recursos administrados.
Se amplió la misma política propuesta con gestión del rol de ejecución exacto y
red etiquetada Checkpoint=6, incluyendo permisos de eliminación. El archivo
compactado tiene 4736 caracteres y cabe en una política administrada de 6144.
No se ejecutará otro apply hasta que esos permisos estén habilitados.
