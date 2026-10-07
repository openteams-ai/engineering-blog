// The shared look of every card in this folder. One file per post, named by
// the post's slug; BlogThumb.astro picks it up by that name.
//
// Hand-made minimal headline art, one vignette per post. Every label and
// number comes from the post itself. All draw in a 720x380 viewBox and
// scale to any card size. Labels are set in Fira Code on cards that show
// code (a command, a file name, an identifier), IBM Plex Sans on the rest.
// Fira Code is loaded at 400 and 500 only, so its labels stop at 500.
//
// Color system (Atlassian-style, restrained): four background families
// rotate across the cards -- soft blue tint, light green tint, peach tint, solid
// brand blue -- plus dark navy. Each tint carries dark ink of its OWN hue,
// and success checks are one green everywhere.
//
// Brand guideline: cold colors. Greens carry no yellow cast: the light
// green family is the old lime turned to the pure-green hue at the same
// lightness and strength. Yellows and oranges are tints and shades of the
// brand gold (#faa944), never a saturated yellow or a burnt orange.
//
// Legibility rule: cards render as small as ~230px wide (a third of the
// canvas), so shapes carry each vignette and text is scarce and LARGE --
// nothing under ~17px on the canvas, key labels 22-36px.

export const code = "var(--font-mono)"; // Fira Code, same as code blocks
export const plex = "var(--font-post)"; // IBM Plex Sans, same as post titles
export const navy = "#091e42";
export const mut = "#5d6575";
// background families
export const softBlue = "#d6e4fa";
export const lightGreen = "#bef6b7";
export const peach = "#fde5c6";
export const solidBlue = "#1d6ae5";
export const darkNavy = "#041437";
// inks
export const blueMut = "#44546f";
export const green = "#216e4e";
export const greenDeep = "#164b35";
export const check = "#22a06b";
// light green family details, light to strong
export const greenWash = "#e5f9e3";
export const greenLine = "#d0f0cc";
export const greenBar = "#a9e6a2";
export const greenDot = "#8ad482";
export const greenOnNavy = "#7fd4a3";
// peach family, light to dark: the brand gold with white or black mixed in
export const peachSoft = "#fddfbb";
export const peachMid = "#fccb8f";
export const gold = "#faa944";
export const goldDeep = "#af7630"; // large text on peach
export const peachInk = "#7d5522"; // small text on peach

// A four-pointed star, centred on (x, y) with radius r.
export const sparkle = (x: number, y: number, r: number) =>
	`M${x} ${y - r}Q${x} ${y} ${x + r} ${y}Q${x} ${y} ${x} ${y + r}Q${x} ${y} ${x - r} ${y}Q${x} ${y} ${x} ${y - r}Z`;
