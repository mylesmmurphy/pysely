const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const webpack = require("webpack");

module.exports = {
  mode: "production",
  entry: { "pyright-worker": "./src/worker.ts" },
  output: {
    path: path.resolve(__dirname, "../docs/assets/intelligence"),
    filename: "[name].js",
  },
  module: {
    rules: [
      { test: /\.ts$/, use: { loader: "ts-loader", options: { transpileOnly: true } } },
      { test: /\.m?js$/, resolve: { fullySpecified: false } },
    ],
  },
  resolve: {
    extensions: [".ts", ".js"],
    alias: {
      fs: "@zenfs/core",
      "node:fs": "@zenfs/core",
      path: "path-browserify",
      "process/browser": require.resolve("process/browser.js"),
    },
    fallback: {
      assert: require.resolve("assert/"),
      buffer: require.resolve("buffer/"),
      child_process: false,
      crypto: false,
      module: false,
      net: false,
      os: require.resolve("os-browserify/browser"),
      readline: false,
      stream: require.resolve("stream-browserify"),
      url: require.resolve("url/"),
      util: require.resolve("util/"),
      v8: false,
      vm: require.resolve("vm-browserify"),
      zlib: require.resolve("browserify-zlib"),
      worker_threads: false,
    },
  },
  plugins: [
    new webpack.ProvidePlugin({ process: "process/browser", Buffer: ["buffer", "Buffer"] }),
    new webpack.DefinePlugin({
      __dirname: JSON.stringify("/"),
      __os_constants: JSON.stringify(os.constants),
      __fs_constants: JSON.stringify(fs.constants),
    }),
  ],
  performance: { hints: false },
};
