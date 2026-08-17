import { useState, useEffect } from 'react';

interface Product {
  id: string;
  name: string;
  price: number;
  imageUrl: string;
}

/**
 * Custom hook to fetch products from the API.
 * Returns an object with products array and loading state.
 */
export const useProducts = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await fetch('/api/products');
        const data = await response.json();
        setProducts(data);
      } catch (error) {
        console.error('Failed to fetch products:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProducts();
  }, []);

  return { products, isLoading };
};
