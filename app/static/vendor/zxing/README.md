# ZXing camera decoder

`zxing-browser.min.js` is the unmodified UMD bundle from `@zxing/browser@0.2.1`
([source](https://github.com/zxing-js/browser), [npm package](https://www.npmjs.com/package/@zxing/browser/v/0.2.1)).
It includes the ZXing library decoder. See `LICENSE-browser.txt` (MIT) and
`LICENSE-library.txt` (Apache-2.0).

The POS loads this local bundle only when opening the camera. It requires no
CDN access or change to the site's Content Security Policy.
