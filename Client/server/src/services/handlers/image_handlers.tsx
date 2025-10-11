import React from "react";
import imageCompression from "browser-image-compression";


export async function useCompress(file: File, max_width_or_height: number = 1000, initial_quality: number = 0.9) {
    const options = {
        maxWidthOrHeight: max_width_or_height,
        useWebWorker: true,
        initialQuality: initial_quality,
    };

    const compressed_img = await imageCompression(file, options);
    return compressed_img;
};

export function useSpoiler() {
    console.log("Not implemented!");
};