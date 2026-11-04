# Configuración trasladada

El entorno Terraform ahora se ejecuta desde [`infra/`](../../infra/), que contiene
`main.tf` y todos los módulos. Se conserva la clave remota
`environments/dev/terraform.tfstate` y las direcciones de recursos existentes.
No ejecutar una configuración nueva desde esta carpeta ni cambiar la clave del
backend. Los archivos locales ignorados de sesiones anteriores no se trasladaron
al repositorio.

Ver el [procedimiento actual](../../docs/iceberg-deployment.md).
