document.addEventListener("DOMContentLoaded", function () {
  const dataElement = document.getElementById("product-variants-data");
  if (!dataElement) {
    console.error("product-variants-data script not found!");
    return;
  }

  const productsVariants = JSON.parse(dataElement.textContent);

  Object.keys(productsVariants).forEach(productId => {
    const colorSelect = document.getElementById(`color-select-${productId}`);
    const sizeSelect = document.getElementById(`size-select-${productId}`);
    const productImg = document.getElementById(`product-img-${productId}`);

    if (!colorSelect || !sizeSelect || !productImg) {
      return;
    }

    function updateSizes() {
      const selectedColor = colorSelect.value;
      const variants = productsVariants[productId].filter(v => v.color === selectedColor);

      sizeSelect.innerHTML = "";
      variants.forEach(variant => {
        const option = document.createElement("option");
        option.value = variant.size;
        option.textContent = variant.size;
        sizeSelect.appendChild(option);
      });

      if (variants.length > 0) {
        productImg.src = variants[0].image_url;
      }
    }

    updateSizes(); // Initial call
    colorSelect.addEventListener("change", updateSizes);
  });
});
