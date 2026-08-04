/** Registro global de los matchers de jest-dom para vitest. */
import '@testing-library/jest-dom/vitest';

/**
 * Carencias de jsdom que Radix necesita para abrirse (Select, Popover, Sheet).
 *
 * jsdom no implementa la Pointer Events API ni `scrollIntoView`, y Radix las
 * usa de verdad en producción — no es un atajo de test: sin estos stubs, abrir
 * un `<Select>` en un test explota con `hasPointerCapture is not a function`,
 * lo que hacía INTESTEABLE la interacción real (elegir una opción) y dejaba
 * pasar solo aserciones sobre el trigger cerrado. Se declara acá, una vez,
 * en vez de repetir mocks por archivo.
 */
if (typeof Element !== 'undefined') {
  Element.prototype.hasPointerCapture ??= () => false;
  Element.prototype.setPointerCapture ??= () => {};
  Element.prototype.releasePointerCapture ??= () => {};
  Element.prototype.scrollIntoView ??= () => {};
}
