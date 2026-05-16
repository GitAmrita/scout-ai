Deploy Scout AI to production (Vercel + Render) by pushing to main.

## Steps

1. Check for uncommitted changes with `git status`
2. If there are uncommitted changes, stage and commit them — ask the user for a commit message if changes are present
3. Push to `main` with `git push origin main`
4. Check which directories changed in the commit (using `git diff --name-only HEAD~1 HEAD`) and confirm the push succeeded with accurate deployment status:
   - If files inside `frontend/` changed: Vercel is auto-deploying — check: https://scout-ai-mu.vercel.app
   - If no `frontend/` files changed: note that Vercel will NOT redeploy (no frontend changes)
   - If files inside `backend/` changed: Render is auto-deploying — check: https://scout-ai-backend-bczu.onrender.com/docs
   - If no `backend/` files changed: note that Render will NOT redeploy (no backend changes)
5. If Render is redeploying, remind the user it may take ~30-60 seconds to wake up if it was idle
