#!/bin/bash

# 1. Create project structure
mkdir -p backend frontend docs .github/workflows uploads processed templates

# 2. Create backend files (copy your FastAPI code)
echo "Creating backend structure..."
# ... copy main.py, requirements.txt, render.yaml to backend/

# 3. Create frontend
echo "Creating frontend..."
# ... copy index.html to frontend/

# 4. Create GitHub workflows
echo "Creating GitHub workflows..."
# ... copy workflow files to .github/workflows/

# 5. Set up GitHub secrets (manual step)
echo ""
echo "Manual steps required:"
echo "1. Go to GitHub repo → Settings → Secrets → Actions"
echo "2. Add these secrets:"
echo "   - RENDER_API_KEY: Get from render.com"
echo "   - RENDER_SERVICE_ID: Get after creating Render service"
echo "   - BACKEND_URL: Your Render app URL (e.g., https://your-app.onrender.com)"

echo "Setup complete!"