# Project Structure Rules

## Directory Organization

### Root Level
- `src/` - Frontend application code
- `backend/` - Backend application code
- `docs/` - Project documentation
- `test/` - Unit tests
- `cypress/` - End-to-end tests
- `migrations/` - Database migrations
- `scripts/` - Build and utility scripts
- `static/` - Static assets
- `kubernetes/` - Kubernetes deployment configurations

### Frontend Structure (`src/`)
- `lib/` - Core application code
  - `components/` - Reusable UI components
  - `stores/` - Svelte stores
  - `apis/` - API client code
  - `utils/` - Utility functions
- `routes/` - SvelteKit routes
- `app.css` - Global styles
- `tailwind.css` - Tailwind configuration
- `app.html` - Main HTML template

### Backend Structure (`backend/`)
- `open_webui/` - Main backend application code
- `migrations/` - Database migrations
- `test/` - Backend tests

## Development Guidelines

### Code Organization
1. Frontend components should be placed in appropriate subdirectories under `src/lib/components/`
2. Backend modules should be organized by functionality in `backend/open_webui/`
3. All configuration files should be in the root directory
4. Tests should be co-located with their respective components/modules

### Naming Conventions
1. Component files should use PascalCase (e.g., `UserProfile.svelte`)
2. Utility files should use camelCase (e.g., `formatDate.ts`)
3. Test files should match their implementation name with `.test` or `.spec` suffix
4. Configuration files should use kebab-case (e.g., `docker-compose.yaml`)

### Code Style
1. Follow Prettier configuration in `.prettierrc`
2. Follow ESLint rules in `.eslintrc.cjs`
3. Use TypeScript for type safety
4. Follow Svelte component best practices
5. Maintain proper separation between frontend and backend concerns

### Testing
1. Write unit tests for all new functionality
2. Add end-to-end tests for critical user flows
3. Follow existing test patterns and conventions
4. Maintain test coverage requirements

### Documentation
1. Keep documentation up to date in the `docs/` directory
2. Update `CHANGELOG.md` for significant changes
3. Document API changes in appropriate backend modules
4. Include JSDoc comments for complex functions

### Build and Deployment
1. Use provided build scripts in `scripts/`
2. Follow Docker deployment patterns
3. Use Makefile for common tasks
4. Keep deployment configurations in appropriate directories

### Version Control
1. Follow Git workflow defined in `.github/`
2. Keep commits focused and atomic
3. Write clear commit messages
4. Update relevant documentation with changes

### Security
1. Keep sensitive information in environment variables
2. Follow security best practices for API endpoints
3. Maintain proper access controls
4. Regular security audits and updates

### Performance
1. Optimize frontend bundle size
2. Implement proper caching strategies
3. Monitor and optimize database queries
4. Follow performance best practices for both frontend and backend 

### Project Startup Process
1. Project Setup:
   - Ensure Python virtual environment is activated: `source .venv/bin/activate`
   - Run `uv sync` in the root directory to update dependencies
   - Navigate to the `backend` directory: `cd backend`
   - Run `./start.sh` to start both backend and frontend servers
   - The start script will:
     - Start the backend server on port 8080
     - Start the frontend development server (automatically finding an available port)
     - Handle environment variables and server configuration
     - Set up Pyodide and required Python packages for the frontend

2. Development Workflow:
   - Always run `uv sync` after making changes to Python dependencies
   - The frontend will automatically hot-reload when changes are made
   - Backend changes require server restart using `./start.sh`
   - Both servers must be running for full application functionality

3. Environment Variables:
   - The backend start script will automatically handle loading environment variables
   - If `WEBUI_SECRET_KEY` is not set, it will be loaded from `.webui_secret_key`
   - Additional environment variables can be set in the backend's `.env` file

4. Common Issues:
   - If the servers fail to start, check the error messages in the terminal
   - The frontend will automatically try the next available port if the default port is in use
   - Ensure all dependencies are properly installed using `uv sync`
   - Check the terminal output for any error messages or warnings 