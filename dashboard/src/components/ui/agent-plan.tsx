"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  Circle,
  CircleAlert,
  CircleDotDashed,
  CircleX,
} from "lucide-react";
import { motion, AnimatePresence, LayoutGroup } from "framer-motion";

interface Subtask {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  tools?: string[];
}

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  level: number;
  dependencies: string[];
  subtasks: Subtask[];
}

const initialTasks: Task[] = [
  {
    id: "1",
    title: "Analyze Server Blueprint",
    description: "Parse the user request to determine the optimal community layout.",
    status: "completed",
    priority: "high",
    level: 0,
    dependencies: [],
    subtasks: [
      {
        id: "1.1",
        title: "Extract core topic and target audience",
        description: "Identify the primary purpose of the server to tailor channels.",
        status: "completed",
        priority: "high",
        tools: ["nlp-processor", "intent-analyzer"],
      },
      {
        id: "1.2",
        title: "Determine channel structure",
        description: "Map out the necessary text, voice, and announcement channels.",
        status: "completed",
        priority: "high",
        tools: ["structure-mapper"],
      },
      {
        id: "1.3",
        title: "Define role hierarchy",
        description: "Establish admin, moderator, premium, and default roles.",
        status: "completed",
        priority: "high",
        tools: ["permission-calculator"],
      },
    ],
  },
  {
    id: "2",
    title: "Provision Infrastructure",
    description: "Execute the API calls to physically create the Discord server components.",
    status: "in-progress",
    priority: "high",
    level: 0,
    dependencies: ["1"],
    subtasks: [
      {
        id: "2.1",
        title: "Create category wrappers",
        description: "Initialize Information, General, and Voice categories.",
        status: "completed",
        priority: "high",
        tools: ["discord-api"],
      },
      {
        id: "2.2",
        title: "Deploy text and voice channels",
        description: "Populate the categories with specific channels.",
        status: "in-progress",
        priority: "high",
        tools: ["discord-api"],
      },
      {
        id: "2.3",
        title: "Establish private admin sectors",
        description: "Create hidden channels for internal moderation logs.",
        status: "pending",
        priority: "medium",
        tools: ["discord-api", "permission-calculator"],
      },
    ],
  },
  {
    id: "3",
    title: "Configure Seromod Security",
    description: "Inject AI moderation parameters and security layers.",
    status: "pending",
    priority: "critical",
    level: 1,
    dependencies: ["2"],
    subtasks: [
      {
        id: "3.1",
        title: "Initialize sanitization filters",
        description: "Deploy the real-time AI input scanner for all channels.",
        status: "pending",
        priority: "high",
        tools: ["sanitization-engine", "redis-cache"],
      },
      {
        id: "3.2",
        title: "Set raid-protection thresholds",
        description: "Define join limits and message velocity caps.",
        status: "pending",
        priority: "high",
        tools: ["rate-limiter"],
      },
      {
        id: "3.3",
        title: "Deploy prompt-injection guards",
        description: "Secure the AI against malicious admin-override attempts.",
        status: "pending",
        priority: "critical",
        tools: ["security-validator"],
      },
    ],
  },
  {
    id: "4",
    title: "Finalize & Boot",
    description: "Complete setup and hand over control to the automated system.",
    status: "pending",
    priority: "high",
    level: 0,
    dependencies: ["3"],
    subtasks: [
      {
        id: "4.1",
        title: "Assign initial bot permissions",
        description: "Grant Seromod the required roles to manage the server.",
        status: "pending",
        priority: "high",
        tools: ["discord-api"],
      },
      {
        id: "4.2",
        title: "Start monitoring loop",
        description: "Activate the main event listener for incoming traffic.",
        status: "pending",
        priority: "high",
        tools: ["event-listener"],
      },
    ],
  },
];

export default function Plan() {
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [expandedTasks, setExpandedTasks] = useState<string[]>(["2"]);
  const [expandedSubtasks, setExpandedSubtasks] = useState<{
    [key: string]: boolean;
  }>({});

  const prefersReducedMotion =
    typeof window !== "undefined"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false;

  const toggleTaskExpansion = (taskId: string) => {
    setExpandedTasks((prev) =>
      prev.includes(taskId)
        ? prev.filter((id) => id !== taskId)
        : [...prev, taskId]
    );
  };

  const toggleSubtaskExpansion = (taskId: string, subtaskId: string) => {
    const key = `${taskId}-${subtaskId}`;
    setExpandedSubtasks((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const toggleTaskStatus = (taskId: string) => {
    setTasks((prev) =>
      prev.map((task) => {
        if (task.id === taskId) {
          const statuses = ["completed", "in-progress", "pending", "need-help", "failed"];
          const currentIndex = Math.floor(Math.random() * statuses.length);
          const newStatus = statuses[currentIndex];
          const updatedSubtasks = task.subtasks.map((subtask) => ({
            ...subtask,
            status: newStatus === "completed" ? "completed" : subtask.status,
          }));
          return { ...task, status: newStatus, subtasks: updatedSubtasks };
        }
        return task;
      })
    );
  };

  const toggleSubtaskStatus = (taskId: string, subtaskId: string) => {
    setTasks((prev) =>
      prev.map((task) => {
        if (task.id === taskId) {
          const updatedSubtasks = task.subtasks.map((subtask) => {
            if (subtask.id === subtaskId) {
              const newStatus = subtask.status === "completed" ? "pending" : "completed";
              return { ...subtask, status: newStatus };
            }
            return subtask;
          });
          const allSubtasksCompleted = updatedSubtasks.every((s) => s.status === "completed");
          return {
            ...task,
            subtasks: updatedSubtasks,
            status: allSubtasksCompleted ? "completed" : task.status,
          };
        }
        return task;
      })
    );
  };

  const taskVariants = {
    hidden: { opacity: 0, y: prefersReducedMotion ? 0 : -5 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: prefersReducedMotion ? "tween" : "spring",
        stiffness: 500,
        damping: 30,
        duration: prefersReducedMotion ? 0.2 : undefined,
      },
    },
    exit: {
      opacity: 0,
      y: prefersReducedMotion ? 0 : -5,
      transition: { duration: 0.15 },
    },
  };

  const subtaskListVariants = {
    hidden: { opacity: 0, height: 0, overflow: "hidden" },
    visible: {
      height: "auto",
      opacity: 1,
      overflow: "visible",
      transition: {
        duration: 0.25,
        staggerChildren: prefersReducedMotion ? 0 : 0.05,
        when: "beforeChildren",
        ease: [0.2, 0.65, 0.3, 0.9],
      },
    },
    exit: {
      height: 0,
      opacity: 0,
      overflow: "hidden",
      transition: { duration: 0.2, ease: [0.2, 0.65, 0.3, 0.9] },
    },
  };

  const subtaskVariants = {
    hidden: { opacity: 0, x: prefersReducedMotion ? 0 : -10 },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        type: prefersReducedMotion ? "tween" : "spring",
        stiffness: 500,
        damping: 25,
        duration: prefersReducedMotion ? 0.2 : undefined,
      },
    },
    exit: {
      opacity: 0,
      x: prefersReducedMotion ? 0 : -10,
      transition: { duration: 0.15 },
    },
  };

  const subtaskDetailsVariants = {
    hidden: { opacity: 0, height: 0, overflow: "hidden" },
    visible: {
      opacity: 1,
      height: "auto",
      overflow: "visible",
      transition: { duration: 0.25, ease: [0.2, 0.65, 0.3, 0.9] },
    },
  };

  const statusBadgeVariants = {
    initial: { scale: 1 },
    animate: {
      scale: prefersReducedMotion ? 1 : [1, 1.08, 1],
      transition: { duration: 0.35, ease: [0.34, 1.56, 0.64, 1] },
    },
  };

  return (
    <div className="w-full h-full overflow-auto p-2">
      <motion.div
        className="bg-black/40 backdrop-blur-md border border-white/20 rounded-lg shadow-xl overflow-hidden text-white"
        initial={{ opacity: 0, y: 10 }}
        animate={{
          opacity: 1,
          y: 0,
          transition: { duration: 0.3, ease: [0.2, 0.65, 0.3, 0.9] },
        }}
      >
        <LayoutGroup>
          <div className="p-4 overflow-hidden">
            <ul className="space-y-1 overflow-hidden">
              {tasks.map((task, index) => {
                const isExpanded = expandedTasks.includes(task.id);
                const isCompleted = task.status === "completed";

                return (
                  <motion.li
                    key={task.id}
                    className={`${index !== 0 ? "mt-1 pt-2" : ""}`}
                    initial="hidden"
                    animate="visible"
                    variants={taskVariants}
                  >
                    <motion.div
                      className="group flex items-center px-3 py-1.5 rounded-md"
                      whileHover={{
                        backgroundColor: "rgba(255,255,255,0.05)",
                        transition: { duration: 0.2 },
                      }}
                    >
                      <motion.div
                        className="mr-2 flex-shrink-0 cursor-pointer"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleTaskStatus(task.id);
                        }}
                        whileTap={{ scale: 0.9 }}
                        whileHover={{ scale: 1.1 }}
                      >
                        <AnimatePresence mode="wait">
                          <motion.div
                            key={task.status}
                            initial={{ opacity: 0, scale: 0.8, rotate: -10 }}
                            animate={{ opacity: 1, scale: 1, rotate: 0 }}
                            exit={{ opacity: 0, scale: 0.8, rotate: 10 }}
                            transition={{ duration: 0.2, ease: [0.2, 0.65, 0.3, 0.9] }}
                          >
                            {task.status === "completed" ? (
                              <CheckCircle2 className="h-4.5 w-4.5 text-green-400" />
                            ) : task.status === "in-progress" ? (
                              <CircleDotDashed className="h-4.5 w-4.5 text-blue-400" />
                            ) : task.status === "need-help" ? (
                              <CircleAlert className="h-4.5 w-4.5 text-yellow-400" />
                            ) : task.status === "failed" ? (
                              <CircleX className="h-4.5 w-4.5 text-red-400" />
                            ) : (
                              <Circle className="text-white/40 h-4.5 w-4.5" />
                            )}
                          </motion.div>
                        </AnimatePresence>
                      </motion.div>

                      <motion.div
                        className="flex min-w-0 flex-grow cursor-pointer items-center justify-between"
                        onClick={() => toggleTaskExpansion(task.id)}
                      >
                        <div className="mr-2 flex-1 truncate">
                          <span className={`${isCompleted ? "text-white/40 line-through" : ""}`}>
                            {task.title}
                          </span>
                        </div>

                        <div className="flex flex-shrink-0 items-center space-x-2 text-xs">
                          {task.dependencies.length > 0 && (
                            <div className="flex items-center mr-2">
                              <div className="flex flex-wrap gap-1">
                                {task.dependencies.map((dep, idx) => (
                                  <motion.span
                                    key={idx}
                                    className="bg-white/10 text-white rounded px-1.5 py-0.5 text-[10px] font-medium shadow-sm"
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ duration: 0.2, delay: idx * 0.05 }}
                                    whileHover={{
                                      y: -1,
                                      backgroundColor: "rgba(255,255,255,0.2)",
                                      transition: { duration: 0.2 },
                                    }}
                                  >
                                    {dep}
                                  </motion.span>
                                ))}
                              </div>
                            </div>
                          )}

                          <motion.span
                            className={`rounded px-1.5 py-0.5 ${
                              task.status === "completed"
                                ? "bg-green-500/20 text-green-300"
                                : task.status === "in-progress"
                                ? "bg-blue-500/20 text-blue-300"
                                : task.status === "need-help"
                                ? "bg-yellow-500/20 text-yellow-300"
                                : task.status === "failed"
                                ? "bg-red-500/20 text-red-300"
                                : "bg-white/10 text-white/60"
                            }`}
                            variants={statusBadgeVariants}
                            initial="initial"
                            animate="animate"
                            key={task.status}
                          >
                            {task.status}
                          </motion.span>
                        </div>
                      </motion.div>
                    </motion.div>

                    <AnimatePresence mode="wait">
                      {isExpanded && task.subtasks.length > 0 && (
                        <motion.div
                          className="relative overflow-hidden"
                          variants={subtaskListVariants}
                          initial="hidden"
                          animate="visible"
                          exit="hidden"
                          layout
                        >
                          <div className="absolute top-0 bottom-0 left-[20px] border-l-2 border-dashed border-white/20" />
                          <ul className="mt-1 mr-2 mb-1.5 ml-3 space-y-0.5">
                            {task.subtasks.map((subtask) => {
                              const subtaskKey = `${task.id}-${subtask.id}`;
                              const isSubtaskExpanded = expandedSubtasks[subtaskKey];

                              return (
                                <motion.li
                                  key={subtask.id}
                                  className="group flex flex-col py-0.5 pl-6"
                                  onClick={() => toggleSubtaskExpansion(task.id, subtask.id)}
                                  variants={subtaskVariants}
                                  initial="hidden"
                                  animate="visible"
                                  exit="exit"
                                  layout
                                >
                                  <motion.div
                                    className="flex flex-1 items-center rounded-md p-1"
                                    whileHover={{
                                      backgroundColor: "rgba(255,255,255,0.05)",
                                      transition: { duration: 0.2 },
                                    }}
                                    layout
                                  >
                                    <motion.div
                                      className="mr-2 flex-shrink-0 cursor-pointer"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        toggleSubtaskStatus(task.id, subtask.id);
                                      }}
                                      whileTap={{ scale: 0.9 }}
                                      whileHover={{ scale: 1.1 }}
                                      layout
                                    >
                                      <AnimatePresence mode="wait">
                                        <motion.div
                                          key={subtask.status}
                                          initial={{ opacity: 0, scale: 0.8, rotate: -10 }}
                                          animate={{ opacity: 1, scale: 1, rotate: 0 }}
                                          exit={{ opacity: 0, scale: 0.8, rotate: 10 }}
                                          transition={{ duration: 0.2, ease: [0.2, 0.65, 0.3, 0.9] }}
                                        >
                                          {subtask.status === "completed" ? (
                                            <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
                                          ) : subtask.status === "in-progress" ? (
                                            <CircleDotDashed className="h-3.5 w-3.5 text-blue-400" />
                                          ) : subtask.status === "need-help" ? (
                                            <CircleAlert className="h-3.5 w-3.5 text-yellow-400" />
                                          ) : subtask.status === "failed" ? (
                                            <CircleX className="h-3.5 w-3.5 text-red-400" />
                                          ) : (
                                            <Circle className="text-white/40 h-3.5 w-3.5" />
                                          )}
                                        </motion.div>
                                      </AnimatePresence>
                                    </motion.div>

                                    <span
                                      className={`cursor-pointer text-sm ${
                                        subtask.status === "completed"
                                          ? "text-white/40 line-through"
                                          : "text-white/90"
                                      }`}
                                    >
                                      {subtask.title}
                                    </span>
                                  </motion.div>

                                  <AnimatePresence mode="wait">
                                    {isSubtaskExpanded && (
                                      <motion.div
                                        className="text-white/60 border-white/20 mt-1 ml-1.5 border-l border-dashed pl-5 text-xs overflow-hidden"
                                        variants={subtaskDetailsVariants}
                                        initial="hidden"
                                        animate="visible"
                                        exit="hidden"
                                        layout
                                      >
                                        <p className="py-1">{subtask.description}</p>
                                        {subtask.tools && subtask.tools.length > 0 && (
                                          <div className="mt-0.5 mb-1 flex flex-wrap items-center gap-1.5">
                                            <span className="text-white/80 font-medium">
                                              System Tools:
                                            </span>
                                            <div className="flex flex-wrap gap-1">
                                              {subtask.tools.map((tool, idx) => (
                                                <motion.span
                                                  key={idx}
                                                  className="bg-white/10 text-white rounded px-1.5 py-0.5 text-[10px] font-medium shadow-sm"
                                                  initial={{ opacity: 0, y: -5 }}
                                                  animate={{
                                                    opacity: 1,
                                                    y: 0,
                                                    transition: { duration: 0.2, delay: idx * 0.05 },
                                                  }}
                                                  whileHover={{
                                                    y: -1,
                                                    backgroundColor: "rgba(255,255,255,0.2)",
                                                    transition: { duration: 0.2 },
                                                  }}
                                                >
                                                  {tool}
                                                </motion.span>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                      </motion.div>
                                    )}
                                  </AnimatePresence>
                                </motion.li>
                              );
                            })}
                          </ul>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.li>
                );
              })}
            </ul>
          </div>
        </LayoutGroup>
      </motion.div>
    </div>
  );
}
