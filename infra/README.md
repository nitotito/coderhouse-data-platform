# Ubicación del Capstone

Terraform se trasladó a `../terraform/`. No se duplicó ni migró el estado remoto.
Para dev, configurar exactamente el backend existente antes de inicializar.
Para pruebas desde cero usar `terraform/isolated/` y un backend independiente.
