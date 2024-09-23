const path = require('path');

module.exports = {
  context: path.resolve(__dirname, 'assets'),
  entry: {
    app: './js/app.js',
    MiradorPreviewer: './js/MiradorPreviewer.js',
  },
  output: {
    path: path.resolve(__dirname, 'static', 'dist'),
    filename: '[name].bundle.js',
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react'],
          },
        },
      },
    ],
  },
  resolve: {
    extensions: ['.js', '.jsx'],
    alias: {
      '@invenio_app_rdm': path.resolve(__dirname, 'assets', 'js', 'invenio_app_rdm'),
      '@invenio_previewer_mirador': path.resolve(__dirname, '../invenio-previewers-mirador/invenio_previewer_mirador/static'),
      '@js': path.resolve(__dirname, 'assets', 'js'),
    },
    fallback: {
      "url": require.resolve("url/"),
    },
  },
  mode: 'development',
};
