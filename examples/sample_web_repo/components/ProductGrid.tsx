'use client';

import { useProducts } from '@/hooks/useProducts';
import { ProductCard } from '@/components/ProductCard';

interface Product {
  id: string;
  name: string;
  price: number;
  imageUrl: string;
}

export const ProductGrid = () => {
  const { products, isLoading } = useProducts();

  if (isLoading) {
    return <div className="animate-pulse text-center text-gray-400">Loading...</div>;
  }

  return (
    <section className="mt-12">
      <h2 className="text-2xl font-bold text-gray-900">Featured Products</h2>
      <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {products.map((product: Product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </section>
  );
};
