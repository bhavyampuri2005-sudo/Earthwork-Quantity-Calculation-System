"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Profile & Totals" },
  { href: "/review", label: "Station Review" },
  { href: "/slopes", label: "Slope Master" },
  { href: "/upload", label: "Upload PDF" },
  { href: "/activity", label: "Activity Log" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="nav">
      {LINKS.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          className={pathname === href ? "active" : ""}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}
