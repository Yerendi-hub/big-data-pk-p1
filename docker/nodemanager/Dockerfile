FROM apache/hadoop:3.4.1

USER root
RUN if command -v dnf >/dev/null; then \
        dnf install -y python3 && dnf clean all; \
    elif command -v apt-get >/dev/null; then \
        apt-get update && apt-get install -y python3 && rm -rf /var/lib/apt/lists/*; \
    else \
        sed -i -e 's/^mirrorlist/#mirrorlist/' \
               -e 's|^#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|' \
               /etc/yum.repos.d/*.repo && \
        yum install -y python3 && yum clean all; \
    fi
USER hadoop