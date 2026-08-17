'use client';

import { useState } from 'react';
import { useCartStore } from '@/hooks/useCartStore';

interface HeroSectionProps {
  title?: string;
  subtitle?: string;
}

export const HeroSection = ({ title = 'Welcome', subtitle }: HeroSectionProps) => {
  const [isVisible, setIsVisible] = useState(true);
  const itemCount = useCartStore((state) => state.items.length);

  if (!isVisible) return null;

  return (
    <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-600 to-purple-700 p-12 text-white">
      <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
      {subtitle && <p className="mt-4 text-lg text-blue-100">{subtitle}</p>}
      <div className="mt-6 flex gap-4">
        <button
          onClick={() => setIsVisible(false)}
          className="rounded-lg bg-white px-6 py-3 font-semibold text-blue-700 shadow-lg transition hover:shadow-xl"
        >
          Get Started
        </button>
        <span className="flex items-center text-sm text-blue-200">
          {itemCount} items in cart
        </span>
      </div>
    </section>
  );
};
