/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // react-pdf ships pdfjs as ESM-only; Next needs to know not to transpile it.
  transpilePackages: ["react-pdf", "pdfjs-dist"],
  webpack: (config) => {
    // pdfjs-dist worker resolution: bundle it client-side.
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
