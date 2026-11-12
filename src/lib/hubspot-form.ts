// Builds a signup for HubSpot's Forms API, which takes JSON straight from the
// browser (no key, no proxy). Pure, so the subscribe box's script stays small
// and this part is tested.

export interface SignupForm {
	portalId: string;
	formGuid: string;
	/** The Engineering Newsletter subscription type the signup opts into. */
	subscriptionTypeId: number;
}

/** What the box says under the email field. HubSpot stores it as the consent given. */
export const CONSENT_TEXT = "By subscribing, you agree to get the Engineering newsletter from OpenTeams. Unsubscribe anytime.";

export const submitUrl = (form: SignupForm) =>
	`https://api.hsforms.com/submissions/v3/integration/submit/${form.portalId}/${form.formGuid}`;

/** The JSON body for one email, with consent to the Engineering Newsletter. */
export function submissionBody(form: SignupForm, email: string, page: { uri: string; name: string }) {
	return {
		fields: [{ objectTypeId: "0-1", name: "email", value: email }],
		context: { pageUri: page.uri, pageName: page.name },
		legalConsentOptions: {
			consent: {
				consentToProcess: true,
				text: CONSENT_TEXT,
				communications: [{ value: true, subscriptionTypeId: form.subscriptionTypeId, text: CONSENT_TEXT }],
			},
		},
	};
}

/** HubSpot's reason for a rejected email, worth showing as is; else undefined. */
export function rejectionMessage(answer: { errors?: { errorType?: string; message?: string }[] }): string | undefined {
	const error = answer.errors?.find((e) => e.errorType?.startsWith("INVALID_EMAIL"));
	return error ? "That email address doesn't look right. Check it and try again." : undefined;
}
