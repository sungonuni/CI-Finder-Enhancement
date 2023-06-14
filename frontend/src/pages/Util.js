/**
 * Check the boolean variable has underbar character.
 * @param {string} TCL 
 * @returns 
 */
 export function IsBoolVarWithUnderbar(TCL) {
  if (TCL.includes("_") === true) {
    return true;
  }
  return false;
}