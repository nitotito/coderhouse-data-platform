
variable "environment" {
  description = "Entorno de despliegue"
  type        = string
}

variable "vpc_cidr" {
  description = "Rango CIDR de la VPC"
  type        = string
}

variable "private_subnet_cidrs" {
  description = "Rangos CIDR de las subredes privadas"
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_cidrs) >= 2
    error_message = "Se requieren al menos dos subredes privadas."
  }
}
