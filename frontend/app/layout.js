import "./globals.css";
import Nav from "@/components/Nav";
import ProjectSelector from "@/components/ProjectSelector";
import { ProjectProvider } from "@/lib/project-context";

export const metadata = {
  title: "Earthwork Quantity System",
  description:
    "OCR-extracted L-section elevation data, cut/fill volumes by Average End Area method",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <ProjectProvider>
          <div className="sheet">
            <header className="titleblock">
              <div className="titleblock-main">
                <div className="titleblock-eyebrow">
                  L-Section · Longitudinal Profile · Scanned Drawing
                </div>
                <h1>Earthwork Quantity Calculation System</h1>
              </div>
              <div className="titleblock-meta">
                <ProjectSelector />
                <div className="titleblock-cell">
                  <span className="k">Method</span>
                  <span className="v">Avg. End Area</span>
                </div>
                <div className="titleblock-cell">
                  <span className="k">Formation W</span>
                  <span className="v">7.85 m</span>
                </div>
              </div>
            </header>
            <Nav />
            <main>{children}</main>
          </div>
        </ProjectProvider>
      </body>
    </html>
  );
}
