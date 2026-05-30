# SYNQMATIC Agency Website

A static website for SYNQMATIC cloud automation agency, built for deployment on GitHub Pages.

## Site Structure

```
agency-site/
├── index.html          # Homepage (hero, about preview, services preview, blog preview)
├── about.html          # About page (team, story, tech stack)
├── services.html       # Services page (projects, packages, retainers, training, FAQ)
├── blog.html           # Blog index (featured post, all posts, newsletter)
├── blog/
│   └── terraform-mistakes.html   # Sample blog post (full article)
├── css/
│   └── style.css       # Full site stylesheet
└── README.md
```

## Deploying to GitHub Pages

1. Create a new GitHub repository (e.g. `synqautomation-site` or `yourusername.github.io`)
2. Push this folder's contents to the `main` branch
3. Go to **Settings → Pages**
4. Set Source to **Deploy from a branch → main → / (root)**
5. Your site will be live at `https://yourusername.github.io/synqautomation-site/`

### Custom Domain (optional)
1. Add a `CNAME` file to the root containing your domain: `synqautomation.io`
2. In your DNS provider, add an A record pointing to GitHub Pages IPs:
   - 185.199.108.153
   - 185.199.109.153
   - 185.199.110.153
   - 185.199.111.153

## Customisation Checklist

Before going live, update the following:

- [ ] Replace `SYNQMATIC` with your chosen agency name throughout all files
- [ ] Replace `hello@synqautomation.io` with your actual email address
- [ ] Update LinkedIn URL in `index.html` contact section
- [ ] Update team bios and certifications in `about.html`
- [ ] Update the stats in the hero section (`index.html`) to reflect your actual experience
- [ ] Replace placeholder blog posts with your real articles
- [ ] Update copyright year and company name in all footer sections

## Adding New Blog Posts

Copy the template structure from `blog/terraform-mistakes.html`.
Update the `<title>`, meta description, tags, content, and related posts section.
Add the post card to `blog.html` in the `all-posts-grid` div.

## Tech Stack

- Pure HTML, CSS, JavaScript — no build tools required
- Google Fonts: Syne (headings) + Space Mono (body/code)
- No dependencies or npm packages
- Fully responsive (mobile, tablet, desktop)
- GitHub Pages compatible (no Jekyll, no config needed)
