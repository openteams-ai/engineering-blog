import { describe, expect, it } from "vitest";
import { CONSENT_TEXT, rejectionMessage, submissionBody, submitUrl } from "./hubspot-form";

const form = { portalId: "123", formGuid: "abc-def", subscriptionTypeId: 42 };

describe("submitUrl", () => {
	it("points at the form's submit endpoint", () => {
		expect(submitUrl(form)).toBe("https://api.hsforms.com/submissions/v3/integration/submit/123/abc-def");
	});
});

describe("submissionBody", () => {
	const body = submissionBody(form, "a@example.com", { uri: "https://x.test/post/", name: "A post" });

	it("sends the email as the contact's email", () => {
		expect(body.fields).toEqual([{ objectTypeId: "0-1", name: "email", value: "a@example.com" }]);
		expect(body.context).toEqual({ pageUri: "https://x.test/post/", pageName: "A post" });
	});

	it("opts into the Engineering Newsletter with the text the reader saw", () => {
		expect(body.legalConsentOptions.consent.communications).toEqual([
			{ value: true, subscriptionTypeId: 42, text: CONSENT_TEXT },
		]);
	});
});

describe("rejectionMessage", () => {
	it("explains a bad email", () => {
		expect(rejectionMessage({ errors: [{ errorType: "INVALID_EMAIL", message: "x" }] })).toMatch(/email address/);
	});

	it("says nothing for other errors", () => {
		expect(rejectionMessage({ errors: [{ errorType: "BLOCKED_EMAIL" }] })).toBeUndefined();
		expect(rejectionMessage({})).toBeUndefined();
	});
});
