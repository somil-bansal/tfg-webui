<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import emojiGroups from '$lib/emoji-groups.json';
	import emojiShortCodes from '$lib/emoji-shortcodes.json';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import VirtualList from '@sveltejs/svelte-virtual-list';

	export let onClose = () => {};
	export let onSubmit = (name) => {};
	export let side = 'top';
	export let align = 'start';
	export let user = null;

	let show = false;
	let emojis = emojiShortCodes;
	let search = '';
	let flattenedEmojis = [];
	let emojiRows = [];

	// Reactive statement to filter the emojis based on search query
	$: {
		if (search) {
			emojis = Object.keys(emojiShortCodes).reduce((acc, key) => {
				if (key.includes(search)) {
					acc[key] = emojiShortCodes[key];
				} else {
					if (Array.isArray(emojiShortCodes[key])) {
						const filtered = emojiShortCodes[key].filter((emoji) => emoji.includes(search));
						if (filtered.length) {
							acc[key] = filtered;
						}
					} else {
						if (emojiShortCodes[key].includes(search)) {
							acc[key] = emojiShortCodes[key];
						}
					}
				}
				return acc;
			}, {});
		} else {
			emojis = emojiShortCodes;
		}
	}
	// Flatten emoji groups and group them into rows of 8 for virtual scrolling
	$: {
		flattenedEmojis = [];
		Object.keys(emojiGroups).forEach((group) => {
			const groupEmojis = emojiGroups[group].filter((emoji) => emojis[emoji]);
			if (groupEmojis.length > 0) {
				flattenedEmojis.push({ type: 'group', label: group });
				flattenedEmojis.push(
					...groupEmojis.map((emoji) => ({
						type: 'emoji',
						name: emoji,
						shortCodes:
							typeof emojiShortCodes[emoji] === 'string'
								? [emojiShortCodes[emoji]]
								: emojiShortCodes[emoji]
					}))
				);
			}
		});
		// Group emojis into rows of 8
		emojiRows = [];
		let currentRow = [];
		flattenedEmojis.forEach((item) => {
			if (item.type === 'emoji') {
				currentRow.push(item);
				if (currentRow.length === 8) {
					emojiRows.push(currentRow);
					currentRow = [];
				}
			} else if (item.type === 'group') {
				if (currentRow.length > 0) {
					emojiRows.push(currentRow); // Push the remaining row
					currentRow = [];
				}
				emojiRows.push([item]); // Add the group label as a separate row
			}
		});
		if (currentRow.length > 0) {
			emojiRows.push(currentRow); // Push the final row
		}
	}
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {
		if (!state) {
			search = '';
			onClose();
		}
	}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>
	<DropdownMenu.Content
		class="max-w-full w-80 bg-gray-50 dark:bg-gray-850 rounded-lg z-9999 shadow-lg dark:text-white"
		sideOffset={8}
		{side}
		{align}
		transition={flyAndScale}
	>
		<div class="mb-1 px-3 pt-2 pb-2">
			<input
				type="text"
				class="w-full text-sm bg-transparent outline-hidden"
				placeholder="Search all emojis"
				bind:value={search}
			/>
		</div>
	</DropdownMenu.Content>
</DropdownMenu.Root>
