import { create } from 'zustand';

interface CartItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
}

interface CartStore {
  items: CartItem[];
  addItem: (product: { id: string; name: string; price: number }) => void;
  removeItem: (id: string) => void;
  clearCart: () => void;
  totalPrice: () => number;
}

export const useCartStore = create<CartStore>((set, get) => ({
  items: [],

  addItem: (product) => {
    set((state) => {
      const existing = state.items.find((item) => item.id === product.id);
      if (existing) {
        return {
          items: state.items.map((item) =>
            item.id === product.id
              ? { ...item, quantity: item.quantity + 1 }
              : item
          ),
        };
      }
      return { items: [...state.items, { ...product, quantity: 1 }] };
    });
  },

  removeItem: (id) => {
    set((state) => ({
      items: state.items.filter((item) => item.id !== id),
    }));
  },

  clearCart: () => set({ items: [] }),

  totalPrice: () => {
    return get().items.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );
  },
}));
