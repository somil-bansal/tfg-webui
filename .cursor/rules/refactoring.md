# Refactoring Rules

## General Principles
1. **Safety First**
   - Always ensure the project can be started and runs before refactoring
   - Keep the project in a working state at all times
   - Make incremental changes rather than large refactors, do not ever create new files and functionailty unless it replaces existing file or function
   - Test after each significant change

2. **Code Organization**
   - Maintain clear separation between frontend and backend code
   - Keep related functionality together
   - Follow the existing project structure
   - Document any structural changes

3. **Dependency Management**
   - Keep dependencies up to date using `uv sync`
   - Document any dependency changes
   - Ensure compatibility between frontend and backend dependencies
   - Remove unused dependencies

4. **Code Quality**
   - Follow existing code style and formatting
   - Maintain type safety (TypeScript for frontend, type hints for Python), do not worry about lint issues, only resolve runtime issues
   - Keep functions and classes focused and single-purpose
   - Improve code readability without changing functionality

5. **Testing**
   - Ensure existing tests pass before refactoring
   - Add tests for new or modified functionality
   - Update tests to reflect refactored code
   - Maintain or improve test coverage



## Refactoring Process
1. **Preparation**
   - Start the project using `source .venv/bin/activate && uv sync && cd backend && ./start.sh`
   - Verify the project is running correctly
   - Document current behavior and performance
   - Create a backup or ensure changes are committed

2. **Implementation**
   - Make changes in small, manageable chunks
   - Test after each significant change
   - Keep the project running throughout
   - Document any issues or decisions

3. **Verification**
   - Ensure all tests pass
   - Verify the project starts correctly
   - Check for any performance regressions
   - Validate all features still work

4. **Cleanup**
   - Remove any temporary code or comments
   - Clean up any unused files or dependencies
   - Commit changes with clear messages

## Specific Guidelines

### Frontend Refactoring
1. **Component Structure**
   - Keep components modular and reusable
   - Follow Svelte best practices
   - Maintain proper prop typing
   - Use stores appropriately

2. **State Management**
   - Keep state management simple and predictable
   - Use appropriate stores for different concerns
   - Avoid prop drilling
   - Document state flow

3. **Styling**
   - Follow existing Tailwind patterns
   - Keep styles scoped to components
   - Maintain responsive design
   - Document any style changes

### Backend Refactoring
1. **API Structure**
   - Maintain RESTful principles
   - Keep endpoints focused and well-documented
   - Use proper HTTP methods
   - Handle errors consistently

2. **Database**
   - Follow existing migration patterns
   - Keep queries efficient
   - Maintain data integrity
   - Document schema changes

3. **Business Logic**
   - Keep business logic exactly same and make sure to never change code fucntionally unelss asked
   - Limit scope of changes to only asked task, never exceed that scope
   - Use appropriate design patterns

## Common Pitfalls to Avoid
1. Breaking existing functionality
2. Making too many changes at once
6. Breaking the build process
8. Making unnecessary changes