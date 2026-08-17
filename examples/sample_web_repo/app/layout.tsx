import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Sample App',
  description: 'A sample Next.js application',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 antialiased">
        {children}
      </body>
    </html>
  );
}
