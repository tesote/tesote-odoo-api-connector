# Docker Development Environment

This guide explains how to use Docker to run Odoo 18.0 locally for testing the Tesote Connector.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB of free RAM
- Port 8069 available

## Quick Start

1. **Start the environment:**
```bash
./bin/docker-dev up
```

2. **First-time setup:**
On first access to http://localhost:8069, if prompted to create a database:
- Master Password: admin
- Database Name: tesote_dev
- Email: admin@tesote.com
- Password: admin
- Language: English
- Country: United States

3. **Access Odoo:**
- URL: http://localhost:8069
- Username: admin
- Password: admin
- Database: tesote_dev

4. **Stop the environment:**
```bash
./bin/docker-dev down
```

## Docker Dev Commands

The `./bin/docker-dev` script provides all necessary commands:

### Basic Operations
```bash
./bin/docker-dev up          # Start environment
./bin/docker-dev down        # Stop environment
./bin/docker-dev restart     # Restart Odoo
./bin/docker-dev status      # Check status
```

### Development
```bash
./bin/docker-dev logs odoo   # View Odoo logs
./bin/docker-dev shell       # Open Odoo Python shell
./bin/docker-dev bash        # Open bash in container
./bin/docker-dev psql        # Open PostgreSQL shell
```

### Testing
```bash
./bin/docker-dev test        # Run tesote_connector tests
./bin/docker-dev install     # Install/update module
```

### Database Management
```bash
./bin/docker-dev backup      # Create database backup
./bin/docker-dev restore backup.sql  # Restore from backup
./bin/docker-dev reset       # Reset database (caution!)
```

## Architecture

The Docker setup includes:

- **PostgreSQL 15**: Database server (internal only, not exposed)
- **Odoo 18.0**: Application server (port 8069)
- **pgAdmin**: Database management UI (port 5050)

## Testing the Connector

1. Start the environment:
```bash
./bin/docker-dev up
```

2. Install the module:
```bash
./bin/docker-dev install
```

3. Configure the connector:
   - Navigate to Connectors → Tesote → Backends
   - Create a new backend with your API credentials
   - Test the connection

4. Run tests:
```bash
./bin/docker-dev test
```

## Module Development

The `tesote_connector` module is mounted as a volume, so changes are reflected immediately:

1. Edit files locally
2. Restart Odoo to reload Python files:
```bash
./bin/docker-dev restart
```

3. For XML/view changes, update the module:
```bash
./bin/docker-dev install
```

## Configuration

### Odoo Configuration
Located at `config/odoo.conf`:
- Dev mode enabled with auto-reload
- Log level set to INFO
- Test mode disabled by default

### Docker Compose
Located at `docker-compose.yml`:
- Persistent volumes for database and filestore
- Health checks for all services
- Automatic module installation
- Development environment configured (`ODOO_ENV=development` + `--dev=all`)

### Switching Between Development and Production Logging

The tesote_connector module automatically adjusts logging verbosity based on environment:

**Development Mode (default in Docker):**
```yaml
environment:
  - ODOO_ENV=development  # Detailed API request/response logs
command: odoo --dev=all
```

**Production Mode (for production deployments):**
```yaml
environment:
  - ODOO_ENV=production  # Minimal console logs, full details in Sentry
command: odoo  # Remove --dev=all flag
```

In development mode, you'll see:
- Full request bodies in console logs
- Full response bodies in console logs
- Rate limit information
- Detailed sync request information

In production mode, you'll see:
- Only high-level summaries in console
- Full details still captured in Sentry breadcrumbs

## Troubleshooting

### Container won't start
```bash
# Check logs
./bin/docker-dev logs

# Clean and restart
./bin/docker-dev clean
./bin/docker-dev up
```

### Module not appearing
```bash
# Update module list
./bin/docker-dev install

# Check logs for errors
./bin/docker-dev logs odoo
```

### Database issues
```bash
# Reset database
./bin/docker-dev reset

# Or restore from backup
./bin/docker-dev restore backups/tesote_dev_*.sql
```

### Port conflicts
If port 8069 is already in use, edit `docker-compose.yml`:
```yaml
ports:
  - "8070:8069"  # Change to different port
```

## Advanced Usage

### Running SQL queries
```bash
./bin/docker-dev psql
# Then run SQL commands
SELECT * FROM tesote_backend;
```

### Python shell access
```bash
./bin/docker-dev shell
# Then use Odoo ORM
>>> env['tesote.backend'].search([])
```

### Debugging
```bash
# Follow logs in real-time
./bin/docker-dev logs -f odoo

# Check container status
docker ps

# Inspect container
docker inspect tesote_odoo
```

## pgAdmin Access

Access pgAdmin at http://localhost:5050:
- Email: admin@tesote.com
- Password: admin

Add server connection:
- Host: db
- Port: 5432
- Username: odoo
- Password: odoo
- Database: tesote_dev
