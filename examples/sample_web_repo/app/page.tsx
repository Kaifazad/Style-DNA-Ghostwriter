import { HeroSection } from '@/components/HeroSection';
import { ProductGrid } from '@/components/ProductGrid';

export default function HomePage() {
  return (
    <main className="container mx-auto px-4 py-8">
      <HeroSection />
      <ProductGrid />
    </main>
  );
}
