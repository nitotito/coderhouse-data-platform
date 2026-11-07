resource "terraform_data" "initialize_platform" {
  count = var.initialize_platform ? 1 : 0
  triggers_replace = [
    try(module.redshift[0].connection.workgroup_arn, ""),
    filesha256("${path.module}/../sql/redshift/01_schemas.sql"),
    filesha256("${path.module}/../sql/redshift/02_streaming.sql"),
    filesha256("${path.module}/../sql/redshift/03_analytics.sql"),
    filesha256("${path.module}/../sql/redshift/04_iceberg.sql"),
    filesha256("${path.module}/../sql/redshift/05_security.sql")
  ]
  provisioner "local-exec" {
    command = "python \"${abspath(path.module)}/../scripts/capstone.py\" initialize --execute"
    environment = {
      CAPSTONE_PROFILE   = coalesce(var.aws_profile, "")
      CAPSTONE_REGION    = var.aws_region
      CAPSTONE_STREAM    = module.kinesis[0].stream_name
      CAPSTONE_DATABASE  = module.lakehouse.database_name
      CAPSTONE_TABLE     = module.lakehouse.table_name
      CAPSTONE_WORKGROUP = module.redshift[0].connection.workgroup
    }
  }
  depends_on = [module.managed_flink, module.redshift]
}
