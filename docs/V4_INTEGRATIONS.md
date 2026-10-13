# v4 integrations and design handoff

- Figma: editable v4 research/validation workflow added to the existing design file: https://www.figma.com/design/bOyjdTtSvzsiQestTOaAoE?node-id=4-2 . The frame is a design handoff, not the executable application.
- Build Web Apps: existing React/Vite design system extended with four researcher screens and native SVG animation.
- Superpowers: roadmap review, isolated implementation, numerical checks and independent review used for v4.
- Context7: official scikit-learn Gradient Boosting documentation consulted for deterministic parameter settings and tuning interactions.
- Sites: published the private v4 fixture preview at https://clinical-trial-workbench-v4.nicespice2.chatgpt.site . Publication status was verified as succeeded for the original v4.0.0 preview; this ZIP-only provider patch does not update that hosted screen. The full Python server is provided in the ZIP.
- Vercel: updating the existing preview project was blocked by a 403 scope authorization error; no CLI credentials were available. The historical Vercel URL is not the v4 delivery.
- AI providers (v4.0.1): OpenAI Responses retained; Gemini generateContent, Claude Messages and an optional OpenAI-compatible Chat Completions adapter added with configurable routing/fallback. Official contracts reviewed. No key is shipped; live account/billing access was not tested.
- GitHub: local CI workflow is included. No v4 remote repository push is claimed.
- tldraw: connection inspection returned no open editable board during v4; no new board edit is claimed.
- MagicPath and Notion: prior private design/document handoffs remain historical; the included v4 source/PDF define this release.
- Neon and Supabase: no hosted service is required. Existing generic PostgreSQL metadata adapter remains optional; no hosted provisioning or Supabase app integration is claimed.
- Railway, Replit and Lovable: no additional deployment was created.
- Runway, OpenArt, HeyGen, Higgsfield and Canva: not runtime dependencies. Precise researcher animations are generated from code and actual inputs, so no paid generated-video service or decorative clinical data is used.
- Tavily and Firecrawl: no extra scraped cohort is introduced; the starter remains the preserved ClinicalTrials.gov API snapshot. Scientific definitions were checked against primary sources.
- Amplitude and Statsig: no analytics trackers or experiments collecting user data are enabled.

Primary technical references: https://scikit-learn.org/stable/modules/calibration.html ; https://scikit-learn.org/stable/modules/model_evaluation.html ; https://scikit-learn.org/stable/modules/ensemble.html ; Angelopoulos and Bates, A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification, https://arxiv.org/abs/2107.07511 . Dependencies remain pinned to the release's tested versions; current online documentation may describe newer versions.
