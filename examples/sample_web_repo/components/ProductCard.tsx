import { useCartStore } from '@/hooks/useCartStore';

interface ProductCardProps {
  product: {
    id: string;
    name: string;
    price: number;
    imageUrl: string;
  };
}

export const ProductCard = ({ product }: ProductCardProps) => {
  const addItem = useCartStore((state) => state.addItem);

  return (
    <div className="group overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition hover:shadow-md">
      <div className="aspect-square overflow-hidden bg-gray-100">
        <img
          src={product.imageUrl}
          alt={product.name}
          className="h-full w-full object-cover transition group-hover:scale-105"
        />
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-gray-900">{product.name}</h3>
        <p className="mt-1 text-sm text-gray-500">${product.price.toFixed(2)}</p>
        <button
          onClick={() => addItem(product)}
          className="mt-3 w-full rounded-lg bg-blue-600 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
        >
          Add to Cart
        </button>
      </div>
    </div>
  );
};
