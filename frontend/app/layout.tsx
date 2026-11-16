import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'SENTINEL AI | Reliability workspace', description: 'Inspectable repository security analysis and a reliability digital twin.' };
export default function Layout({children}: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body>{children}</body></html> }
