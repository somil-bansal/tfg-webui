<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import { settings } from '$lib/stores';


	let toastId = null;

	export let message = '';
	export let type = 'info';
	export let duration = 3000;
	export let position = 'bottom-right';

	$: if (message) {
		if (toastId) {
			toast.dismiss(toastId);
		}

		toastId = toast[type](message, {
			duration,
			position
		});
	}
</script>

{#if message}
	<div class="toast" role="alert">
		<div class="alert alert-{type}">
			<span>{message}</span>
		</div>
	</div>
{/if}
