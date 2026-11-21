FROM python:3.12-slim
ARG TERRAFORM_VERSION=1.12.2
RUN apt-get update && apt-get install -y --no-install-recommends unzip curl && rm -rf /var/lib/apt/lists/*
RUN curl -fsSLo /tmp/tf.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && unzip /tmp/tf.zip -d /usr/local/bin && rm /tmp/tf.zip
RUN pip install --no-cache-dir terraform-local==0.24.1 python-hcl2==7.3.1
WORKDIR /workspace/terraform/local
ENTRYPOINT ["sh", "-c"]
CMD ["tflocal init -input=false && tflocal apply -auto-approve -input=false"]
