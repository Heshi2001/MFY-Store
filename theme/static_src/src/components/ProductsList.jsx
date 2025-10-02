import React, { useEffect, useState } from "react";

export default function ProductsList() {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    fetch("/api/products/?dealer=Qikink")
      .then((r) => r.json())
      .then((data) => setProducts(data.results || data));
  }, []);

  return (
    <div className="grid grid-cols-3 gap-4">
      {products.map((p) => (
        <div key={p.id} className="card p-4 shadow rounded">
           {/* ✅ API already ensures placeholder */}
          <img
            src={p.main_thumbnail_url}  
            alt={p.name}
            className="w-full h-48 object-cover"
          />
          <h3 className="text-lg font-semibold">{p.name}</h3>
          <p className="text-gray-700">₹{p.offer_price || p.price}</p>
          <button className="bg-blue-500 text-white px-3 py-1 rounded mt-2">
            Add to cart
          </button>
        </div>
      ))}
    </div>
  );
}
