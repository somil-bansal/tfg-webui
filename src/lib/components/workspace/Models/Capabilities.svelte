<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { marked } from 'marked';

	

	const helpText = {
		vision: 'Model accepts image inputs',
		usage: 
			'Sends `stream_options: { include_usage: true }` in the request.\nSupported providers will return token usage information in the response when set.'
		,
		citations: 'Displays citations in the response'
	};

	export let capabilities: {
		vision?: boolean;
		usage?: boolean;
		citations?: boolean;
	} = {};
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-sm font-semibold">{'Capabilities'}</div>
	</div>
	<div class="flex">
		{#each Object.keys(capabilities) as capability}
			<div class=" flex items-center gap-2 mr-3">
				<Checkbox
					state={capabilities[capability] ? 'checked' : 'unchecked'}
					on:change={(e) => {
						capabilities[capability] = e.detail === 'checked';
					}}
				/>

				<div class=" py-0.5 text-sm capitalize">
					<Tooltip content={marked.parse(helpText[capability])}>
						{capability}
					</Tooltip>
				</div>
			</div>
		{/each}
	</div>
</div>
