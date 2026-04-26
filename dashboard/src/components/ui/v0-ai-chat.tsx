"use client";

import { useEffect, useRef, useCallback } from "react";
import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
    ArrowUpIcon,
    Paperclip,
    PlusIcon,
} from "lucide-react";

interface UseAutoResizeTextareaProps {
    minHeight: number;
    maxHeight?: number;
}

function useAutoResizeTextarea({
    minHeight,
    maxHeight,
}: UseAutoResizeTextareaProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const adjustHeight = useCallback(
        (reset?: boolean) => {
            const textarea = textareaRef.current;
            if (!textarea) return;

            if (reset) {
                textarea.style.height = `${minHeight}px`;
                return;
            }

            textarea.style.height = `${minHeight}px`;

            const newHeight = Math.max(
                minHeight,
                Math.min(
                    textarea.scrollHeight,
                    maxHeight ?? Number.POSITIVE_INFINITY
                )
            );

            textarea.style.height = `${newHeight}px`;
        },
        [minHeight, maxHeight]
    );

    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = `${minHeight}px`;
        }
    }, [minHeight]);

    useEffect(() => {
        const handleResize = () => adjustHeight();
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, [adjustHeight]);

    return { textareaRef, adjustHeight };
}

import { Loader2 } from "lucide-react";

export function VercelV0Chat({ 
    prompt, 
    setPrompt, 
    onSubmit, 
    isProcessing 
}: { 
    prompt: string; 
    setPrompt: (value: string) => void; 
    onSubmit: () => void;
    isProcessing: boolean;
}) {
    const { textareaRef, adjustHeight } = useAutoResizeTextarea({
        minHeight: 60,
        maxHeight: 200,
    });

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (prompt.trim() && !isProcessing) {
                onSubmit();
            }
        }
    };

    return (
        <div className="flex flex-col items-center w-full max-w-4xl mx-auto p-4 space-y-8">
            <h1 className="text-4xl font-bold text-white drop-shadow-lg">
                How can Seromod assist your server?
            </h1>

            <div className="w-full">
                <div className="relative bg-transparent backdrop-blur-md rounded-xl border border-white/20 shadow-2xl">
                    <div className="overflow-y-auto">
                        <Textarea
                            ref={textareaRef}
                            value={prompt}
                            onChange={(e) => {
                                setPrompt(e.target.value);
                                adjustHeight();
                            }}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask Seromod to configure rules, handle raids, or manage roles..."
                            className={cn(
                                "w-full px-4 py-3",
                                "resize-none",
                                "bg-transparent",
                                "border-none",
                                "text-white text-sm",
                                "focus:outline-none",
                                "focus-visible:ring-0 focus-visible:ring-offset-0",
                                "placeholder:text-white/50 placeholder:text-sm",
                                "min-h-[60px]"
                            )}
                            style={{
                                overflow: "hidden",
                            }}
                            disabled={isProcessing}
                        />
                    </div>

                    <div className="flex items-center justify-between p-3 border-t border-white/10">
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                className="group p-2 hover:bg-white/10 rounded-lg transition-colors flex items-center gap-1 cursor-default opacity-50"
                            >
                                <Paperclip className="w-4 h-4 text-white" />
                                <span className="text-xs text-white/60 hidden group-hover:inline transition-opacity">
                                    Attach logs (Coming soon)
                                </span>
                            </button>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                className="px-2 py-1 rounded-lg text-sm text-white/60 transition-colors border border-dashed border-white/30 hover:border-white/50 hover:bg-white/10 flex items-center justify-between gap-1 cursor-default opacity-50"
                            >
                                <PlusIcon className="w-4 h-4" />
                                Context
                            </button>
                            <button
                                type="button"
                                onClick={onSubmit}
                                disabled={!prompt.trim() || isProcessing}
                                className={cn(
                                    "px-1.5 py-1.5 rounded-lg text-sm transition-colors border border-white/30 flex items-center justify-between gap-1",
                                    prompt.trim() && !isProcessing
                                        ? "bg-white text-black hover:bg-gray-200"
                                        : "text-white/60 hover:border-white/50 hover:bg-white/10"
                                )}
                            >
                                {isProcessing ? (
                                    <Loader2 className="w-4 h-4 text-white/60 animate-spin" />
                                ) : (
                                    <ArrowUpIcon
                                        className={cn(
                                            "w-4 h-4",
                                            prompt.trim()
                                                ? "text-black"
                                                : "text-white/60"
                                        )}
                                    />
                                )}
                                <span className="sr-only">Send</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
