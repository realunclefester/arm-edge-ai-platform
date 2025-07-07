FROM pgvector/pgvector:pg16

# Install dependencies for pg_net with retry logic
RUN apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    --no-install-recommends \
    -o Dpkg::Options::="--force-confdef" \
    -o Dpkg::Options::="--force-confold" \
    ca-certificates \
    build-essential \
    git \
    postgresql-server-dev-16 \
    libcurl4-openssl-dev \
    pkg-config \
    || (echo "Retrying apt-get after 5 seconds..." && sleep 5 && \
        apt-get update -qq && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y \
        --no-install-recommends \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        ca-certificates \
        build-essential \
        git \
        postgresql-server-dev-16 \
        libcurl4-openssl-dev \
        pkg-config) \
    && rm -rf /var/lib/apt/lists/*

# Install pg_net
WORKDIR /tmp
RUN git clone https://github.com/supabase/pg_net.git
WORKDIR /tmp/pg_net
RUN export PG_CONFIG=/usr/lib/postgresql/16/bin/pg_config && make && make install

# Cleanup
RUN rm -rf /tmp/pg_net

# Add pg_net to shared_preload_libraries
RUN echo "shared_preload_libraries = 'pg_net'" >> /usr/share/postgresql/postgresql.conf.sample

# Copy custom entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /

# Set custom entrypoint
ENTRYPOINT ["./entrypoint.sh"]
CMD ["postgres"]